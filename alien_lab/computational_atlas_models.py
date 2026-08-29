from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SemanticRequest:
    task_id: str
    representation: str
    public_input: dict[str, Any]


@dataclass(frozen=True)
class SemanticResult:
    status: str
    task_ir: dict[str, Any] | None
    model_calls: int
    error: str | None = None


class SemanticCompiler(Protocol):
    def compile(self, request: SemanticRequest) -> SemanticResult: ...


@dataclass(frozen=True)
class RouteRequest:
    task_id: str
    task_ir: dict[str, Any]
    available_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class RouteResult:
    status: str
    selected_capabilities: tuple[str, ...]
    model_calls: int
    error: str | None = None


class Router(Protocol):
    def route(self, request: RouteRequest) -> RouteResult: ...


def unavailable_model_evidence(model_class: str, reason: str) -> dict[str, Any]:
    return {
        "model_class": model_class,
        "status": "MODEL_UNAVAILABLE",
        "score": None,
        "reason": reason,
        "model_calls": 0,
    }


def build_production_fitness_record(
    capability: str,
    contribution: float,
    domains: list[str],
    *,
    model_calls_displaced: float = 0.0,
    confidence: str = "INITIAL_REFERENCE_EVIDENCE",
) -> dict[str, Any]:
    seam_by_capability = {
        "G": "ToolPort or KernelPort behind a graph-capability adapter",
        "L": "ToolPort or KernelPort behind a logic-capability adapter",
        "C": "ToolPort or KernelPort behind a constraint-capability adapter",
        "P": "ToolPort or KernelPort behind a planner-capability adapter",
        "X": "contained KernelPort program-execution capability",
        "M": "ToolPort or KernelPort numerical-capability adapter",
        "D": "ToolPort analytical-data adapter",
        "R": "ToolPort retrieval/evidence adapter",
    }
    return {
        "capability": capability,
        "measured_contribution": contribution,
        "affected_domains": sorted(set(domains)),
        "model_calls_displaced": model_calls_displaced,
        "composition_compatibility": "TaskIR typed input/output; measure before promotion",
        "determinism": "reference adapter deterministic for identical validated inputs",
        "verification_contract": {
            "input": "versioned TaskIR fragment",
            "result": "typed capability result",
            "evidence": "immutable execution/certificate payload",
            "independent_check": "replay or capability-specific deterministic verifier when available",
        },
        "resource_estimate": {
            "cpu": "MEASURE_ON_TARGET_HOST",
            "ram": "MEASURE_ON_TARGET_HOST",
            "vram": "NONE_EXPECTED_FOR_REFERENCE_ENGINE",
            "storage": "MEASURE_ON_TARGET_HOST",
            "latency": "MEASURE_ON_TARGET_HOST",
            "idle": "MEASURE_ON_TARGET_HOST",
        },
        "isolation_requirement": "supervised adapter or contained kernel; no direct production-state access",
        "state_requirement": "stateless unless a promoted implementation explicitly declares durable derived state",
        "failure_containment": "typed capability failure; authoritative V31M4 state remains unchanged",
        "replaceability_contract": "provider-neutral capability contract; implementation is replaceable",
        "v31m4_integration_seam": seam_by_capability.get(capability, "candidate capability boundary requires architecture review"),
        "roadmap_displacement": "MEASURE_FROM_010_RESIDUAL_FAILURES_BEFORE_CHANGING_V31M4_PLAN",
        "engineering_estimate": "ESTIMATE_AFTER_MATURE_IMPLEMENTATION_SELECTION",
        "evidence_confidence": confidence,
        "promotion_status": "EXPERIMENTAL",
    }
