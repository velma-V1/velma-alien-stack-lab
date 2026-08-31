from __future__ import annotations

import json
from typing import Any

from .computational_atlas_engines import run_engine
from .computational_atlas_live_types import ModelRequest, ModelResponse
from .computational_atlas_providers import parse_model_json
from .computational_atlas_surfaces import INTENT_BY_CAPABILITY, LEGAL_INTENTS, UnboundOperation, UnboundTaskIR, task_ir_json_schema


CAPABILITY_BY_INTENT = {intent: capability for capability, intent in INTENT_BY_CAPABILITY.items() if capability != "U"}

SEMANTIC_SYSTEM_PROMPT = (
    "Convert the supplied problem into the exact JSON TaskIR schema. "
    "Do not solve the task. Preserve every operation, value, relationship, and requested order. "
    "The legal intent values are exactly: " + ", ".join(LEGAL_INTENTS) + ". "
    "Choose only from those interface values; never invent missing facts."
)

DIRECT_SYSTEM_PROMPT = (
    "Solve the supplied problem exactly. Return JSON with one key named result whose value is an array "
    "containing one outcome per requested item in the required order."
)


def semantic_call_budget(arm: str) -> int:
    budgets = {"FREE_JSON": 1, "SCHEMA_CONSTRAINED": 1, "SCHEMA_VALIDATE_REPAIR": 2}
    if arm not in budgets:
        raise ValueError(f"unknown semantic arm: {arm}")
    return budgets[arm]


def unbound_from_dict(data: dict[str, Any]) -> UnboundTaskIR:
    operations = tuple(
        UnboundOperation(
            operation_id=str(item["operation_id"]),
            intent=str(item["intent"]),
            payload=dict(item["payload"]),
        )
        for item in data.get("operations", [])
    )
    return UnboundTaskIR(task_id=str(data.get("task_id", "")), operations=operations, verification=tuple(data.get("verification", [])))


def validate_unbound_ir(ir: UnboundTaskIR) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not ir.task_id:
        errors.append("missing_task_id")
    if not ir.operations:
        errors.append("missing_operations")
    ids: set[str] = set()
    for operation in ir.operations:
        if not operation.operation_id or operation.operation_id in ids:
            errors.append("invalid_or_duplicate_operation_id")
        ids.add(operation.operation_id)
        if operation.intent not in CAPABILITY_BY_INTENT and operation.intent != "unclassified_problem":
            errors.append(f"unknown_intent:{operation.intent}")
        if not isinstance(operation.payload, dict):
            errors.append(f"invalid_payload:{operation.operation_id}")
    return not errors, errors


def deterministic_route(ir: UnboundTaskIR) -> tuple[str, ...]:
    routed = []
    for operation in ir.operations:
        capability = CAPABILITY_BY_INTENT.get(operation.intent)
        if capability is None:
            return ()
        routed.append(capability)
    return tuple(routed)


def execute_unbound(ir: UnboundTaskIR) -> tuple[bool, tuple[Any, ...], list[str]]:
    capabilities = deterministic_route(ir)
    if len(capabilities) != len(ir.operations):
        return False, (), ["unroutable_intent"]
    values: list[Any] = []
    errors: list[str] = []
    for capability, operation in zip(capabilities, ir.operations):
        result = run_engine(capability, operation.payload, {})
        if not result.ok:
            errors.append(result.error or "engine_error")
            return False, tuple(values), errors
        values.append(result.value)
    return True, tuple(values), errors


def compile_with_provider(
    provider: Any,
    *,
    request_id: str,
    surface: dict[str, Any],
    constrained: bool,
    images: tuple[Any, ...] = (),
) -> tuple[ModelResponse, UnboundTaskIR | None, list[str]]:
    prompt = SEMANTIC_SYSTEM_PROMPT + "\nINPUT:\n" + json.dumps(surface, sort_keys=True)
    response = provider.complete(ModelRequest(
        request_id=request_id,
        prompt=prompt,
        json_schema=task_ir_json_schema() if constrained else None,
        images=images,
        max_output_tokens=2048,
    ))
    if not response.ok:
        return response, None, [response.error_kind or "model_error"]
    try:
        parsed = parse_model_json(response)
    except Exception:
        return response, None, ["json_parse_error"]
    try:
        ir = unbound_from_dict(parsed)
    except Exception as exc:
        return response, None, [f"ir_decode:{type(exc).__name__}"]
    valid, errors = validate_unbound_ir(ir)
    return response, ir if valid else None, errors
