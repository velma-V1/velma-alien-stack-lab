from __future__ import annotations

from collections import Counter
from typing import Any

from .computational_atlas_engines import CAPABILITIES, run_engine
from .computational_atlas_worlds import World


MAP_NAMES = (
    "computational_coverage",
    "minimum_basis",
    "unique_engine_value",
    "synergy_matrix",
    "substitution_redundancy",
    "semantic_degradation",
    "semantic_error_taxonomy",
    "decomposition_error_rate",
    "routing_regret",
    "tool_overload",
    "model_dependence_pareto",
    "verification_value",
    "silent_wrong_rate",
    "capability_learning",
    "transfer_drift",
    "horizon_curve",
    "frontier_gap",
    "missing_capability_clusters",
    "rescue_bottlenecks",
    "next_direction_pareto",
)

RESCUE_ORDER = (
    "SEMANTIC",
    "DECOMPOSITION",
    "ROUTING",
    "ENGINE",
    "COMPOSITION",
    "EXECUTION",
    "VERIFICATION",
)


def _solve_world(world: World) -> bool:
    if world.outside_basis:
        return False
    values = []
    for operation in world.task_ir.operations:
        result = run_engine(operation.capability, operation.payload, {})
        if not result.ok:
            return False
        values.append(result.value)
    return tuple(values) == world.expected_result


def run_rescue_probe(world: World, injected_fault: str) -> dict[str, Any]:
    """Controlled harness audit for rescue localization.

    This deliberately injects a known failure stage. It proves that the rescue
    accounting and localization machinery behaves correctly; it is not live
    evidence that a neural semantic compiler exhibits that failure distribution.
    """
    if injected_fault == "MISSING_CAPABILITY" or world.outside_basis:
        return {
            "world_id": world.world_id,
            "evidence_kind": "CONTROLLED_RESCUE_AUDIT",
            "injected_fault": injected_fault,
            "original_score": 0,
            "rescued_score": 0,
            "rescued": False,
            "localized_bottleneck": "MISSING_CAPABILITY",
            "interventions": [{"stage": stage, "success": False} for stage in RESCUE_ORDER],
        }
    if injected_fault not in RESCUE_ORDER:
        raise ValueError(f"unsupported rescue fault: {injected_fault}")
    downstream_success = _solve_world(world)
    fault_index = RESCUE_ORDER.index(injected_fault)
    interventions = []
    for index, stage in enumerate(RESCUE_ORDER):
        interventions.append({
            "stage": stage,
            "success": bool(downstream_success and index >= fault_index),
        })
    return {
        "world_id": world.world_id,
        "evidence_kind": "CONTROLLED_RESCUE_AUDIT",
        "injected_fault": injected_fault,
        "original_score": 0,
        "rescued_score": 1 if downstream_success else 0,
        "rescued": bool(downstream_success),
        "localized_bottleneck": injected_fault if downstream_success else "MISSING_CAPABILITY",
        "interventions": interventions,
    }


def build_accumulation_audit(seed: int, lineage_count: int = 48) -> dict[str, Any]:
    if lineage_count < 1:
        raise ValueError("lineage_count must be positive")
    stages = (
        "NOVEL",
        "REPEAT",
        "PARAMETER_VARIATION",
        "REPRESENTATION_SHIFT",
        "ENVIRONMENT_DRIFT",
        "COMPOSITION_TRANSFER",
    )
    arm_reasoning_stages = {
        "NO_RETAINED_CAPABILITY": set(stages),
        "TEXT_MEMORY": {"NOVEL", "PARAMETER_VARIATION", "REPRESENTATION_SHIFT", "COMPOSITION_TRANSFER"},
        "VERIFIED_EXECUTABLE_CAPABILITY": {"NOVEL", "REPRESENTATION_SHIFT", "COMPOSITION_TRANSFER"},
    }
    arms: dict[str, Any] = {}
    for arm, reasoning_stages in arm_reasoning_stages.items():
        reasoning_calls = lineage_count * len(reasoning_stages)
        reuse_events = lineage_count * (len(stages) - len(reasoning_stages))
        arms[arm] = {
            "reasoning_calls": reasoning_calls,
            "reuse_events": reuse_events,
            "incorrect_reuse": 0,
            "verified_successes": lineage_count * len(stages),
            "total_events": lineage_count * len(stages),
        }
    return {
        "seed": int(seed),
        "evidence_kind": "SYNTHETIC_MECHANISM_AUDIT",
        "lineages": lineage_count,
        "stages_per_lineage": len(stages),
        "stages": list(stages),
        "arms": arms,
        "interpretation_limit": "Mechanism/accounting proof only; not live-model capability evidence.",
    }


def _synergy_candidates(worlds: list[World]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for world in worlds:
        required = sorted(set(world.required_capabilities))
        if world.outside_basis or len(required) < 2:
            continue
        for left_index, left in enumerate(required):
            for right in required[left_index + 1:]:
                counts[f"{left}+{right}"] += 1
    return dict(sorted(counts.items()))


def _missing_clusters(worlds: list[World]) -> dict[str, int]:
    counts = Counter(world.family for world in worlds if world.outside_basis)
    return dict(sorted(counts.items()))


def build_discovery_report(*, worlds: list[World], phase_maps: dict[str, Any]) -> dict[str, Any]:
    maps: dict[str, Any] = {
        "computational_coverage": phase_maps.get("computational_coverage", {}),
        "minimum_basis": phase_maps.get("minimum_basis", {}),
        "unique_engine_value": phase_maps.get("unique_engine_value", phase_maps.get("leave_one_out", {})),
        "synergy_matrix": _synergy_candidates(worlds),
        "substitution_redundancy": phase_maps.get("leave_one_out", {}),
        "semantic_degradation": {"status": "PENDING_LOCAL_MODEL_EVIDENCE", "representations": ["R0", "R1", "R2", "R3", "R4", "R5"]},
        "semantic_error_taxonomy": {"status": "PENDING_LOCAL_MODEL_EVIDENCE"},
        "decomposition_error_rate": {"status": "PENDING_LOCAL_MODEL_EVIDENCE"},
        "routing_regret": {"status": "PENDING_ROUTER_EVIDENCE"},
        "tool_overload": {"status": "PENDING_ROUTER_EVIDENCE"},
        "model_dependence_pareto": {"status": "PENDING_LOCAL_MODEL_EVIDENCE"},
        "verification_value": {"status": "PARTIALLY_MEASURED", "deterministic_reference_verification": True},
        "silent_wrong_rate": {"status": "PENDING_EFFECT_FAULT_EVIDENCE"},
        "capability_learning": build_accumulation_audit(seed=20260829, lineage_count=48),
        "transfer_drift": {"status": "MECHANISM_AUDIT_AVAILABLE_LIVE_EVIDENCE_PENDING"},
        "horizon_curve": {"status": "PENDING_LONG_HORIZON_PHASE"},
        "frontier_gap": {"status": "PENDING_FRONTIER_CALIBRATION"},
        "missing_capability_clusters": _missing_clusters(worlds),
        "rescue_bottlenecks": {"status": "CONTROLLED_AUDIT_READY_LIVE_DISTRIBUTION_PENDING"},
        "next_direction_pareto": [
            {"direction": "semantic_compiler", "why": "009 proved exact computation after formalization; representation generalization remains unmeasured"},
            {"direction": "missing_operator_discovery", "why": "outside-basis probes are preserved and clustered instead of scored as infrastructure failure"},
            {"direction": "typed_composition", "why": "multi-capability worlds expose handoff and orchestration bottlenecks"},
            {"direction": "production_adapter_selection", "why": "reference engines must be replaced by mature V31M4-compatible implementations before promotion"},
        ],
    }
    if set(maps) != set(MAP_NAMES):
        raise AssertionError("discovery map contract drift")
    return {
        "conclusion_semantics": "DISCOVERY_NOT_PASS_FAIL",
        "maps": maps,
        "capability_basis": list(CAPABILITIES),
        "valid_unresolved_is_evidence": True,
    }
