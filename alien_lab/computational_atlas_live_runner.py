from __future__ import annotations

import json
from typing import Any

from .computational_atlas_composition import build_composition_worlds, execute_composition
from .computational_atlas_engines import CAPABILITIES, run_engine
from .computational_atlas_live_types import LiveImage, ModelRequest
from .computational_atlas_providers import ModelProvider
from .computational_atlas_routing import DECOY_TOOL_CATALOG, REAL_TOOL_CATALOG, catalog_for_condition, oracle_route, rule_route
from .computational_atlas_semantics import (
    DIRECT_SYSTEM_PROMPT,
    SEMANTIC_SYSTEM_PROMPT,
    compile_with_provider,
    execute_unbound,
    unbound_from_dict,
    validate_unbound_ir,
)
from .computational_atlas_surfaces import UnboundOperation, UnboundTaskIR, oracle_unbound_ir, render_live_surface, task_ir_json_schema
from .computational_atlas_worlds import World, build_worlds


_REAL_NAME_TO_CAPABILITY = {tool["name"]: tool["capability"] for tool in REAL_TOOL_CATALOG}
_DECOY_NAMES = {tool["name"] for tool in DECOY_TOOL_CATALOG}


def _images_for_surface(surface: dict[str, Any]) -> tuple[LiveImage, ...]:
    image = surface.get("image")
    if not isinstance(image, dict):
        return ()
    return (LiveImage(media_type=str(image["media_type"]), base64_data=str(image["base64_data"]), sha256=str(image["sha256"])),)


def _score_result(world: World, result: Any) -> dict[str, Any]:
    if world.outside_basis or world.expected_result is None:
        return {"status": "VALID_UNRESOLVED_MISSING_CAPABILITY", "score": 0, "verified": False, "result": result}
    if isinstance(result, list):
        observed = tuple(result)
    elif isinstance(result, tuple):
        observed = result
    else:
        observed = (result,)
    verified = observed == tuple(world.expected_result)
    return {
        "status": "VERIFIED_SUCCESS" if verified else "VALID_UNRESOLVED_VERIFICATION",
        "score": 1 if verified else 0,
        "verified": verified,
        "result": list(observed),
    }


def _execute_ir_against_world(world: World, ir: UnboundTaskIR) -> dict[str, Any]:
    if world.outside_basis:
        return {"status": "VALID_UNRESOLVED_MISSING_CAPABILITY", "score": 0, "verified": False, "result": None, "errors": ["OUTSIDE_INITIAL_BASIS"]}
    ok, values, errors = execute_unbound(ir)
    if not ok:
        return {"status": "VALID_UNRESOLVED_ENGINE", "score": 0, "verified": False, "result": list(values), "errors": errors}
    scored = _score_result(world, values)
    scored["errors"] = errors
    return scored


def _infer_intent_from_payload(payload: dict[str, Any]) -> str | None:
    keys = set(payload)
    if {"edges", "start", "goal"} <= keys:
        return "path_query"
    if {"facts", "rules", "query"} <= keys:
        return "rule_entailment"
    if {"items", "budget"} <= keys:
        return "budget_selection"
    if {"transitions", "start", "goal"} <= keys:
        return "state_goal_search"
    if {"program", "return"} <= keys:
        return "program_transform"
    if {"operation", "values"} <= keys:
        return "numeric_aggregate"
    if {"left", "right", "left_key", "right_key", "sum_field"} <= keys:
        return "record_join_aggregate"
    if {"query_terms", "records", "top_k"} <= keys:
        return "evidence_rank"
    return None


def _deterministic_recognize(world: World, representation: str) -> UnboundTaskIR | None:
    surface = render_live_surface(world, representation)
    operations: list[UnboundOperation] = []
    if representation == "R1_STRUCTURED":
        items = (surface.get("content") or {}).get("items", [])
        for index, item in enumerate(items):
            payload = item.get("facts") if isinstance(item, dict) else None
            if not isinstance(payload, dict):
                return None
            intent = _infer_intent_from_payload(payload)
            if intent is None:
                return None
            operations.append(UnboundOperation(f"recognized-{index:02d}", intent, payload))
    elif representation == "R4_IMPLICIT":
        groups = (surface.get("content") or {}).get("groups", [])
        for index, group in enumerate(groups):
            payload = group.get("records") if isinstance(group, dict) else None
            if not isinstance(payload, dict):
                return None
            intent = _infer_intent_from_payload(payload)
            if intent is None:
                return None
            operations.append(UnboundOperation(f"recognized-{index:02d}", intent, payload))
    else:
        return None
    return UnboundTaskIR(task_id=world.task_ir.task_id, operations=tuple(operations), verification=tuple(world.task_ir.verification))


def _provider_direct_result(provider: ModelProvider, *, request_id: str, world: World, representation: str) -> dict[str, Any]:
    surface = render_live_surface(world, representation)
    prompt = DIRECT_SYSTEM_PROMPT + "\nINPUT:\n" + json.dumps({k: v for k, v in surface.items() if k != "image"}, sort_keys=True)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["result"],
        "properties": {"result": {"type": "array"}},
    }
    response = provider.complete(ModelRequest(
        request_id=request_id,
        prompt=prompt,
        json_schema=schema,
        images=_images_for_surface(surface),
        max_output_tokens=2048,
    ))
    if not response.ok:
        status = "VALID_UNRESOLVED_SEMANTIC" if response.error_kind != "TRANSPORT" else "INVALID_INFRASTRUCTURE"
        return {
            "status": status,
            "score": 0 if status != "INVALID_INFRASTRUCTURE" else None,
            "verified": False,
            "result": None,
            "model_calls": response.model_calls,
            "error_kind": response.error_kind,
            "error": response.error,
            "evidence_kind": response.evidence_kind,
        }
    parsed = response.parsed_json
    if parsed is None:
        try:
            parsed = json.loads(response.text)
        except Exception:
            parsed = None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("result"), list):
        return {"status": "VALID_UNRESOLVED_SEMANTIC", "score": 0, "verified": False, "result": None, "model_calls": response.model_calls, "error_kind": "MALFORMED_OUTPUT", "evidence_kind": response.evidence_kind}
    scored = _score_result(world, parsed["result"])
    scored.update({"model_calls": response.model_calls, "evidence_kind": response.evidence_kind, "prompt_tokens": response.prompt_tokens, "output_tokens": response.output_tokens, "duration_ms": response.duration_ms})
    return scored


def run_phase_c_cell(cell: Any, provider: ModelProvider | None) -> dict[str, Any]:
    world = build_worlds(seed=20260910, count=192)[int(cell.world_index)]
    base = {"cell_id": cell.cell_id, "phase": "C", "arm": cell.arm, "world_id": world.world_id, "representation": cell.representation}
    if cell.arm == "ORACLE_IR_BASIS":
        outcome = _execute_ir_against_world(world, oracle_unbound_ir(world))
        outcome.update({"model_calls": 0, "evidence_kind": "ORACLE_DOWNSTREAM_CEILING"})
        return {**base, **outcome}
    if cell.arm == "DETERMINISTIC_RECOGNIZER_BASIS":
        ir = _deterministic_recognize(world, str(cell.representation))
        if ir is None:
            return {**base, "status": "VALID_UNRESOLVED_SEMANTIC", "score": 0, "verified": False, "result": None, "model_calls": 0, "evidence_kind": "LIVE_DETERMINISTIC_EVIDENCE"}
        outcome = _execute_ir_against_world(world, ir)
        outcome.update({"model_calls": 0, "evidence_kind": "LIVE_DETERMINISTIC_EVIDENCE"})
        return {**base, **outcome}
    if cell.arm == "MODEL_DIRECT":
        if provider is None:
            return {**base, "status": "INVALID_INFRASTRUCTURE", "score": None, "verified": False, "result": None, "model_calls": 0, "error": "MODEL_PROVIDER_REQUIRED"}
        return {**base, **_provider_direct_result(provider, request_id=cell.cell_id, world=world, representation=str(cell.representation))}
    if cell.arm == "LOCAL_SEMANTIC_COMPILER_BASIS":
        if provider is None:
            return {**base, "status": "INVALID_INFRASTRUCTURE", "score": None, "verified": False, "result": None, "model_calls": 0, "error": "MODEL_PROVIDER_REQUIRED"}
        surface = render_live_surface(world, str(cell.representation))
        response, ir, errors = compile_with_provider(
            provider,
            request_id=cell.cell_id,
            surface={k: v for k, v in surface.items() if k != "image"},
            constrained=True,
            images=_images_for_surface(surface),
        )
        if not response.ok or ir is None:
            status = "INVALID_INFRASTRUCTURE" if response.error_kind == "TRANSPORT" else "VALID_UNRESOLVED_SEMANTIC"
            return {**base, "status": status, "score": None if status == "INVALID_INFRASTRUCTURE" else 0, "verified": False, "result": None, "model_calls": response.model_calls, "semantic_errors": errors, "evidence_kind": response.evidence_kind}
        outcome = _execute_ir_against_world(world, ir)
        outcome.update({"model_calls": response.model_calls, "semantic_errors": errors, "evidence_kind": response.evidence_kind, "prompt_tokens": response.prompt_tokens, "output_tokens": response.output_tokens, "duration_ms": response.duration_ms})
        return {**base, **outcome}
    raise ValueError(f"unknown Phase C arm: {cell.arm}")


def rescue_phase_c_outcome(original: dict[str, Any], world: World) -> dict[str, Any]:
    rescued = _execute_ir_against_world(world, oracle_unbound_ir(world))
    return {
        "evidence_kind": "RESCUE_DIAGNOSTIC",
        "world_id": world.world_id,
        "original_score": original.get("score"),
        "original_status": original.get("status"),
        "rescued_score": rescued.get("score"),
        "rescued_status": rescued.get("status"),
        "localized_bottleneck": "SEMANTIC" if original.get("score") == 0 and rescued.get("score") == 1 else "MISSING_CAPABILITY",
    }


def _compile_once(provider: ModelProvider, *, request_id: str, world: World, representation: str, constrained: bool, repair_context: str | None = None) -> tuple[Any, UnboundTaskIR | None, list[str]]:
    surface = render_live_surface(world, representation)
    prompt = SEMANTIC_SYSTEM_PROMPT
    if repair_context:
        prompt += "\nYour previous TaskIR was rejected for: " + repair_context + ". Correct only the representation; do not solve the task."
    prompt += "\nINPUT:\n" + json.dumps({k: v for k, v in surface.items() if k != "image"}, sort_keys=True)
    response = provider.complete(ModelRequest(
        request_id=request_id,
        prompt=prompt,
        json_schema=task_ir_json_schema() if constrained else None,
        images=_images_for_surface(surface),
        max_output_tokens=2048,
    ))
    if not response.ok:
        return response, None, [response.error_kind or "model_error"]
    parsed = response.parsed_json
    if parsed is None:
        try:
            parsed = json.loads(response.text)
        except Exception:
            return response, None, ["json_parse_error"]
    try:
        ir = unbound_from_dict(parsed)
    except Exception as exc:
        return response, None, [f"ir_decode:{type(exc).__name__}"]
    valid, errors = validate_unbound_ir(ir)
    return response, ir if valid else None, errors


def run_phase_d_cell(cell: Any, provider: ModelProvider | None) -> dict[str, Any]:
    if provider is None:
        return {"cell_id": cell.cell_id, "phase": "D", "status": "INVALID_INFRASTRUCTURE", "score": None, "model_calls": 0, "error": "MODEL_PROVIDER_REQUIRED"}
    world = build_worlds(seed=20260911, count=192)[int(cell.world_index)]
    constrained = cell.arm in {"SCHEMA_CONSTRAINED", "SCHEMA_VALIDATE_REPAIR"}
    first, ir, errors = _compile_once(provider, request_id=cell.cell_id + "-1", world=world, representation=str(cell.representation), constrained=constrained)
    calls = first.model_calls
    repair_used = False
    outcome: dict[str, Any] | None = None
    if first.ok and ir is not None:
        outcome = _execute_ir_against_world(world, ir)
    needs_repair = cell.arm == "SCHEMA_VALIDATE_REPAIR" and (outcome is None or outcome.get("score") != 1)
    if needs_repair:
        repair_used = True
        context = ";".join(errors or ([str(outcome.get("status"))] if outcome else ["invalid TaskIR"]))
        second, repaired_ir, repair_errors = _compile_once(provider, request_id=cell.cell_id + "-2", world=world, representation=str(cell.representation), constrained=True, repair_context=context)
        calls += second.model_calls
        errors = repair_errors
        if second.ok and repaired_ir is not None:
            outcome = _execute_ir_against_world(world, repaired_ir)
        else:
            outcome = None
    if outcome is None:
        status = "INVALID_INFRASTRUCTURE" if first.error_kind == "TRANSPORT" else "VALID_UNRESOLVED_SEMANTIC"
        return {"cell_id": cell.cell_id, "phase": "D", "arm": cell.arm, "status": status, "score": None if status == "INVALID_INFRASTRUCTURE" else 0, "verified": False, "result": None, "model_calls": calls, "repair_used": repair_used, "semantic_errors": errors, "evidence_kind": first.evidence_kind}
    return {"cell_id": cell.cell_id, "phase": "D", "arm": cell.arm, **outcome, "model_calls": calls, "repair_used": repair_used, "semantic_errors": errors, "evidence_kind": first.evidence_kind}


def _tool_names_for_capabilities(capabilities: tuple[str, ...]) -> tuple[str, ...]:
    reverse = {tool["capability"]: tool["name"] for tool in REAL_TOOL_CATALOG}
    return tuple(reverse[capability] for capability in capabilities)


def _execute_selected_tools(world: World, selected_tools: tuple[str, ...]) -> dict[str, Any]:
    if any(name not in _REAL_NAME_TO_CAPABILITY for name in selected_tools):
        return {"status": "VALID_UNRESOLVED_ROUTING", "score": 0, "verified": False, "result": None}
    selected_capabilities = tuple(_REAL_NAME_TO_CAPABILITY[name] for name in selected_tools)
    required = tuple(operation.capability for operation in world.task_ir.operations)
    if any(capability not in selected_capabilities for capability in required):
        return {"status": "VALID_UNRESOLVED_ROUTING", "score": 0, "verified": False, "result": None}
    values = []
    for operation in world.task_ir.operations:
        result = run_engine(operation.capability, operation.payload, {})
        if not result.ok:
            return {"status": "VALID_UNRESOLVED_ENGINE", "score": 0, "verified": False, "result": values}
        values.append(result.value)
    return _score_result(world, values)


def run_phase_e_cell(cell: Any, provider: ModelProvider | None) -> dict[str, Any]:
    world = build_worlds(seed=20260912, count=192)[int(cell.world_index)]
    ir = oracle_unbound_ir(world)
    catalog = catalog_for_condition(str(cell.condition))
    model_calls = 0
    if cell.arm == "ORACLE_ROUTER":
        selected = _tool_names_for_capabilities(oracle_route(ir))
        evidence_kind = "ORACLE_ROUTING_CEILING"
    elif cell.arm == "RULE_ROUTER":
        selected = rule_route(ir, catalog)
        evidence_kind = "LIVE_DETERMINISTIC_EVIDENCE"
    elif cell.arm == "LOCAL_MODEL_ROUTER":
        if provider is None:
            return {"cell_id": cell.cell_id, "phase": "E", "status": "INVALID_INFRASTRUCTURE", "score": None, "model_calls": 0, "error": "MODEL_PROVIDER_REQUIRED"}
        schema = {"type": "object", "additionalProperties": False, "required": ["selected_tools"], "properties": {"selected_tools": {"type": "array", "items": {"type": "string"}}}}
        prompt = "Select only the tools necessary to execute this formal task. Return JSON selected_tools.\nTASK:\n" + json.dumps(ir.to_dict(), sort_keys=True) + "\nTOOLS:\n" + json.dumps(list(catalog), sort_keys=True)
        response = provider.complete(ModelRequest(cell.cell_id, prompt, json_schema=schema, max_output_tokens=2048))
        model_calls = response.model_calls
        evidence_kind = response.evidence_kind
        if not response.ok:
            status = "INVALID_INFRASTRUCTURE" if response.error_kind == "TRANSPORT" else "VALID_UNRESOLVED_ROUTING"
            return {"cell_id": cell.cell_id, "phase": "E", "status": status, "score": None if status == "INVALID_INFRASTRUCTURE" else 0, "model_calls": model_calls, "decoy_selection_rate": 0.0, "evidence_kind": evidence_kind}
        parsed = response.parsed_json
        if not isinstance(parsed, dict):
            try:
                parsed = json.loads(response.text)
            except Exception:
                parsed = {}
        selected = tuple(str(name) for name in parsed.get("selected_tools", []) if isinstance(name, str))
    else:
        raise ValueError(cell.arm)
    decoy_count = sum(name in _DECOY_NAMES for name in selected)
    decoy_rate = decoy_count / max(1, len(selected))
    outcome = _execute_selected_tools(world, selected)
    required_names = set(_tool_names_for_capabilities(tuple(operation.capability for operation in world.task_ir.operations)))
    selected_real = {name for name in selected if name in _REAL_NAME_TO_CAPABILITY}
    precision = len(required_names & selected_real) / max(1, len(selected_real))
    recall = len(required_names & selected_real) / max(1, len(required_names))
    return {"cell_id": cell.cell_id, "phase": "E", "arm": cell.arm, **outcome, "selected_tools": list(selected), "model_calls": model_calls, "decoy_selection_rate": decoy_rate, "precision": precision, "recall": recall, "evidence_kind": evidence_kind}


def run_phase_f_cell(cell: Any, provider: ModelProvider | None) -> dict[str, Any]:
    world = build_composition_worlds(seed=20260913, count=96)[int(cell.world_index)]
    if cell.arm == "MODEL_DIRECT":
        if provider is None:
            return {"cell_id": cell.cell_id, "phase": "F", "status": "INVALID_INFRASTRUCTURE", "score": None, "model_calls": 0, "error": "MODEL_PROVIDER_REQUIRED"}
        # Naturalized paired task: operation payloads are provided, engine assignments remain hidden from the model.
        prompt = DIRECT_SYSTEM_PROMPT + "\nCHAINED TASK:\n" + json.dumps([{"step": i + 1, "facts": op.payload} for i, op in enumerate(world.operations)], sort_keys=True)
        schema = {"type": "object", "required": ["result"], "properties": {"result": {"type": "array"}}}
        response = provider.complete(ModelRequest(cell.cell_id, prompt, json_schema=schema, max_output_tokens=2048))
        if not response.ok:
            status = "INVALID_INFRASTRUCTURE" if response.error_kind == "TRANSPORT" else "VALID_UNRESOLVED_COMPOSITION"
            return {"cell_id": cell.cell_id, "phase": "F", "status": status, "score": None if status == "INVALID_INFRASTRUCTURE" else 0, "verified": False, "model_calls": response.model_calls, "evidence_kind": response.evidence_kind}
        parsed = response.parsed_json if isinstance(response.parsed_json, dict) else {}
        result = parsed.get("result")
        verified = isinstance(result, list) and tuple(result) == tuple(world.expected_result)
        return {"cell_id": cell.cell_id, "phase": "F", "status": "VERIFIED_SUCCESS" if verified else "VALID_UNRESOLVED_COMPOSITION", "score": 1 if verified else 0, "verified": verified, "result": result, "model_calls": response.model_calls, "evidence_kind": response.evidence_kind}
    if cell.arm.startswith("SINGLE_"):
        capability = cell.arm.removeprefix("SINGLE_")
        result = execute_composition(world, (capability,), typed_handoff=True)
    elif cell.arm == "ALL_ENGINES_NO_TYPED_HANDOFF":
        result = execute_composition(world, CAPABILITIES, typed_handoff=False)
    elif cell.arm in {"TYPED_COMPOSITION", "TYPED_COMPOSITION_VERIFIED"}:
        result = execute_composition(world, CAPABILITIES, typed_handoff=True)
    else:
        raise ValueError(cell.arm)
    return {
        "cell_id": cell.cell_id,
        "phase": "F",
        "arm": cell.arm,
        "status": result["status"],
        "score": 1 if result["verified"] else 0,
        "verified": result["verified"],
        "result": list(result["values"]),
        "model_calls": 0,
        "first_broken_handoff": result.get("first_broken_handoff"),
        "measured_synergy_candidate": bool(result["verified"] and len(world.required_capabilities) > 1 and cell.arm in {"TYPED_COMPOSITION", "TYPED_COMPOSITION_VERIFIED"}),
        "evidence_kind": "LIVE_DETERMINISTIC_EVIDENCE",
    }
