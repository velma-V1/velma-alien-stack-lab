from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .computational_atlas_engines import CAPABILITIES, run_engine
from .computational_atlas_types import Operation, stable_hash


@dataclass(frozen=True)
class Binding:
    producer_operation: str
    consumer_operation: str
    target_path: tuple[Any, ...]
    transform: str


@dataclass(frozen=True)
class CompositionWorld:
    world_id: str
    required_capabilities: tuple[str, ...]
    operations: tuple[Operation, ...]
    bindings: tuple[Binding, ...]
    expected_result: tuple[Any, ...]
    seed: int


def _transform(value: Any, kind: str) -> Any:
    if kind == "identity":
        return value
    if kind == "number":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (list, tuple, dict, str)):
            return len(value)
        return 0
    if kind == "positive_int":
        base = _transform(value, "number")
        return 1 + (abs(int(base)) % 2)
    if kind == "bool":
        return bool(value)
    if kind == "node":
        return "v" + stable_hash(value)[:8]
    raise ValueError(f"unknown binding transform: {kind}")


def _set_path(payload: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    current: Any = payload
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def _base_payload(capability: str, index: int, *, dynamic_hint: Any = None) -> tuple[dict[str, Any], tuple[Any, ...], str]:
    n = 3 + index % 5
    if capability == "G":
        node = _transform(dynamic_hint, "node") if dynamic_hint is not None else f"g{index}a"
        return ({"edges": [[node, f"g{index}b"], [f"g{index}b", f"g{index}c"]], "start": None if dynamic_hint is not None else node, "goal": f"g{index}c"}, ("start",), "node")
    if capability == "L":
        return ({"facts": {"seed": None if dynamic_hint is not None else True}, "rules": [["seed", "mid"], ["mid", "goal"]], "query": "goal"}, ("facts", "seed"), "bool")
    if capability == "C":
        return ({"items": [{"id": "a", "cost": 1, "value": n}, {"id": "b", "cost": 2, "value": n + 4}, {"id": "c", "cost": 4, "value": n + 5}], "budget": None if dynamic_hint is not None else 3}, ("budget",), "positive_int")
    if capability == "P":
        node = _transform(dynamic_hint, "node") if dynamic_hint is not None else f"p{index}a"
        return ({"transitions": {node: [f"p{index}b"], f"p{index}b": [f"p{index}g"], f"p{index}g": []}, "start": None if dynamic_hint is not None else node, "goal": f"p{index}g"}, ("start",), "node")
    if capability == "X":
        return ({"program": [{"op": "set", "name": "value", "value": None if dynamic_hint is not None else n}, {"op": "mul", "name": "value", "value": 2}, {"op": "add", "name": "value", "value": 1}], "return": "value"}, ("program", 0, "value"), "number")
    if capability == "M":
        return ({"operation": "weighted_mean", "values": [None if dynamic_hint is not None else n, n + 2, n + 4], "weights": [1, 2, 1]}, ("values", 0), "number")
    if capability == "D":
        return ({"left": [{"id": 1}, {"id": 2}], "right": [{"id": 1, "amount": None if dynamic_hint is not None else n}, {"id": 2, "amount": n + 1}], "left_key": "id", "right_key": "id", "sum_field": "amount"}, ("right", 0, "amount"), "number")
    if capability == "R":
        return ({"query_terms": ["alpha", "shared"], "records": [{"id": "r1", "terms": ["alpha", "shared"], "authority": 2}, {"id": "r2", "terms": ["shared"], "authority": 3}, {"id": "r3", "terms": ["alpha"], "authority": 1}], "top_k": None if dynamic_hint is not None else 1}, ("top_k",), "positive_int")
    raise ValueError(capability)


def _chain_capabilities(index: int, count: int) -> tuple[str, ...]:
    start = (index * 5 + index // 3) % len(CAPABILITIES)
    return tuple(CAPABILITIES[(start + offset) % len(CAPABILITIES)] for offset in range(count))


def build_composition_worlds(seed: int = 20260913, count: int = 96) -> list[CompositionWorld]:
    if count != 96:
        raise ValueError("frozen Phase F requires exactly 96 worlds")
    worlds: list[CompositionWorld] = []
    for index in range(count):
        required_count = 2 + index // 24
        capabilities = _chain_capabilities(index, required_count)
        operations: list[Operation] = []
        bindings: list[Binding] = []
        outputs: dict[str, Any] = {}
        expected: list[Any] = []
        previous_id: str | None = None
        previous_value: Any = None
        for position, capability in enumerate(capabilities):
            op_id = f"cf-{index:03d}-{position:02d}"
            payload, target_path, transform = _base_payload(capability, index * 7 + position, dynamic_hint=previous_value if position else None)
            if position:
                bindings.append(Binding(previous_id or "", op_id, target_path, transform))
                _set_path(payload, target_path, _transform(previous_value, transform))
            result = run_engine(capability, payload, {})
            if not result.ok:
                raise AssertionError(f"composition generator produced invalid operation {capability}: {result.error}")
            operation = Operation(op_id, capability, payload)
            operations.append(operation)
            outputs[op_id] = result.value
            expected.append(result.value)
            previous_id = op_id
            previous_value = result.value
        worlds.append(CompositionWorld(
            world_id=f"CF-{seed}-{index:03d}-{stable_hash([seed, index, capabilities])[:8]}",
            required_capabilities=capabilities,
            operations=tuple(operations),
            bindings=tuple(bindings),
            expected_result=tuple(expected),
            seed=seed,
        ))
    return worlds


def execute_composition(world: CompositionWorld, capabilities: tuple[str, ...], *, typed_handoff: bool) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    values: list[Any] = []
    binding_by_consumer = {binding.consumer_operation: binding for binding in world.bindings}
    for operation in world.operations:
        if operation.capability not in capabilities:
            return {"verified": False, "status": "VALID_UNRESOLVED_ENGINE", "values": tuple(values), "first_broken_handoff": None}
        payload = deepcopy(operation.payload)
        binding = binding_by_consumer.get(operation.operation_id)
        if binding is not None:
            if not typed_handoff:
                return {"verified": False, "status": "VALID_UNRESOLVED_COMPOSITION", "values": tuple(values), "first_broken_handoff": binding.consumer_operation}
            if binding.producer_operation not in outputs:
                return {"verified": False, "status": "VALID_UNRESOLVED_COMPOSITION", "values": tuple(values), "first_broken_handoff": binding.consumer_operation}
            _set_path(payload, binding.target_path, _transform(outputs[binding.producer_operation], binding.transform))
        result = run_engine(operation.capability, payload, {})
        if not result.ok:
            return {"verified": False, "status": "VALID_UNRESOLVED_ENGINE", "values": tuple(values), "first_broken_handoff": operation.operation_id}
        outputs[operation.operation_id] = result.value
        values.append(result.value)
    verified = tuple(values) == world.expected_result
    return {"verified": verified, "status": "VERIFIED_SUCCESS" if verified else "VALID_UNRESOLVED_VERIFICATION", "values": tuple(values), "first_broken_handoff": None}
