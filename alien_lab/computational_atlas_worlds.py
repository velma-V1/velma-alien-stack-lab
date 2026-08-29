from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any

from .computational_atlas_engines import CAPABILITIES, run_engine
from .computational_atlas_types import Operation, TaskIR, stable_hash


FAMILIES = (
    "dependency_workflow",
    "resource_allocation",
    "scheduling",
    "policy_rule_reasoning",
    "state_space_planning",
    "quantitative_engineering",
    "record_data_synthesis",
    "software_code",
    "evidence_reconciliation",
    "temporal_spatial",
    "scientific_diagnostic",
    "multi_domain_operational",
)

CAPABILITY_NAMES = {
    "G": "dependency and path reasoning",
    "L": "rule entailment",
    "C": "resource optimization",
    "P": "state-space planning",
    "X": "program execution",
    "M": "quantitative calculation",
    "D": "record joining and aggregation",
    "R": "evidence retrieval",
}


@dataclass(frozen=True)
class World:
    world_id: str
    family: str
    task_ir: TaskIR
    required_capabilities: tuple[str, ...]
    expected_result: tuple[Any, ...] | None
    outside_basis: bool
    seed: int
    difficulty: int

    def sealed_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "family": self.family,
            "task_ir": self.task_ir.to_dict(include_required=True),
            "required_capabilities": list(self.required_capabilities),
            "expected_result": list(self.expected_result) if self.expected_result is not None else None,
            "outside_basis": self.outside_basis,
            "seed": self.seed,
            "difficulty": self.difficulty,
            "sealed_hash": stable_hash({
                "world_id": self.world_id,
                "task_ir": self.task_ir.to_dict(include_required=True),
                "expected_result": self.expected_result,
            }),
        }

    def render(self, representation: str) -> dict[str, Any]:
        if representation == "R0_ORACLE_IR":
            return {"world_id": self.world_id, "representation": representation, "task_ir": self.task_ir.to_dict(include_required=True)}
        public_operations = [
            {
                "problem": CAPABILITY_NAMES.get(op.capability, "unfamiliar operation"),
                "details": op.payload,
                "sequence": index + 1,
            }
            for index, op in enumerate(self.task_ir.operations)
        ]
        if representation == "R1_STRUCTURED":
            request: Any = {"work_items": public_operations, "goal": "produce and verify the result of every work item in sequence"}
        elif representation == "R2_NATURAL":
            phrases = [f"step {item['sequence']} needs {item['problem']} using the supplied details" for item in public_operations]
            request = "Please solve this job carefully: " + "; then ".join(phrases) + "."
            request = {"request": request, "details": [item["details"] for item in public_operations]}
        elif representation == "R3_PARAPHRASED":
            phrases = [f"work item {item['sequence']} involves {item['problem']}" for item in reversed(public_operations)]
            request = {"request": "Some notes are out of order. " + "; ".join(phrases), "details": [item["details"] for item in reversed(public_operations)], "noise": ["ignore decorative ordering", "verify before concluding"]}
        elif representation == "R4_IMPLICIT":
            request = {"request": "Infer the necessary operations from these mixed records and return one verified combined result.", "records": [item["details"] for item in public_operations]}
        elif representation == "R5_PERCEPTUAL":
            request = {"artifact_rows": [{"row": item["sequence"], "label": item["problem"], "cells": item["details"]} for item in public_operations]}
        else:
            raise ValueError(f"unsupported representation: {representation}")
        return {"world_id": self.world_id, "representation": representation, "surface": request}


def _payload(capability: str, index: int) -> dict[str, Any]:
    n = index % 7 + 2
    if capability == "G":
        return {"edges": [[f"n{index}a", f"n{index}b"], [f"n{index}b", f"n{index}c"], [f"n{index}a", f"n{index}x"], [f"n{index}x", f"n{index}c"]], "start": f"n{index}a", "goal": f"n{index}c"}
    if capability == "L":
        return {"facts": {f"fact{index}": True}, "rules": [[f"fact{index}", f"mid{index}"], [f"mid{index}", f"goal{index}"]], "query": f"goal{index}"}
    if capability == "C":
        return {"items": [{"id": f"i{index}a", "cost": 2, "value": n + 5}, {"id": f"i{index}b", "cost": 3, "value": n + 7}, {"id": f"i{index}c", "cost": 6, "value": n + 8}], "budget": 5}
    if capability == "P":
        return {"transitions": {f"s{index}0": [f"s{index}1", f"s{index}2"], f"s{index}1": [f"s{index}g"], f"s{index}2": [f"s{index}d"], f"s{index}d": [], f"s{index}g": []}, "start": f"s{index}0", "goal": f"s{index}g"}
    if capability == "X":
        return {"program": [{"op": "set", "name": "value", "value": n}, {"op": "mul", "name": "value", "value": 3}, {"op": "add", "name": "value", "value": index % 5}], "return": "value"}
    if capability == "M":
        return {"operation": "weighted_mean", "values": [n, n + 4, n + 8], "weights": [1, 2, 1]}
    if capability == "D":
        return {"left": [{"id": index * 10 + 1}, {"id": index * 10 + 2}], "right": [{"id": index * 10 + 1, "amount": n}, {"id": index * 10 + 2, "amount": n + 3}, {"id": index * 10 + 3, "amount": 999}], "left_key": "id", "right_key": "id", "sum_field": "amount"}
    if capability == "R":
        return {"query_terms": [f"topic{index}", "shared"], "records": [{"id": f"e{index}a", "terms": [f"topic{index}"], "authority": 2}, {"id": f"e{index}b", "terms": [f"topic{index}", "shared"], "authority": 1}, {"id": f"e{index}c", "terms": ["shared"], "authority": 3}], "top_k": 2}
    return {"opaque_problem": f"outside-{index}", "observations": [n, n + 1, n + 3]}


def _required_count(index: int) -> int:
    if index < 64:
        return 1
    if index < 128:
        return 2
    if index < 168:
        return 3
    if index < 184:
        return 4 + (index % 2)
    return 0


def _capability_tuple(index: int, count: int) -> tuple[str, ...]:
    if count == 0:
        return ("U",)
    start = (index * 3 + index // 8) % len(CAPABILITIES)
    return tuple(CAPABILITIES[(start + offset) % len(CAPABILITIES)] for offset in range(count))


def _expected(operations: tuple[Operation, ...]) -> tuple[Any, ...] | None:
    values = []
    for op in operations:
        result = run_engine(op.capability, op.payload, {})
        if not result.ok:
            return None
        values.append(result.value)
    return tuple(values)


def build_worlds(seed: int, count: int = 192) -> list[World]:
    if count < 1 or count > 192:
        raise ValueError("count must be between 1 and 192")
    rng = random.Random(seed)
    worlds: list[World] = []
    for index in range(count):
        required_count = _required_count(index)
        required = _capability_tuple(index, required_count)
        outside = required_count == 0
        capabilities = required if not outside else ("U",)
        operations = tuple(
            Operation(
                operation_id=f"op-{index:03d}-{position:02d}",
                capability=capability,
                payload=_payload(capability, index * 11 + position),
            )
            for position, capability in enumerate(capabilities)
        )
        task_ir = TaskIR(
            task_id=f"world-{seed}-{index:03d}",
            entities=({"world": index, "family_slot": index % len(FAMILIES)},),
            facts=({"difficulty": 1 + index // 24, "salt": rng.randrange(1_000_000)},),
            goals=({"kind": "verified_combined_result"},),
            verification=({"kind": "exact_sequence_equality"},),
            provenance=({"generator": "experiment-010", "seed": seed},),
            required_capabilities=required,
            operations=operations,
        )
        worlds.append(World(
            world_id=f"W{index:03d}-{stable_hash([seed, index])[:8]}",
            family=FAMILIES[index % len(FAMILIES)],
            task_ir=task_ir,
            required_capabilities=required,
            expected_result=None if outside else _expected(operations),
            outside_basis=outside,
            seed=seed,
            difficulty=1 + index // 24,
        ))
    return worlds
