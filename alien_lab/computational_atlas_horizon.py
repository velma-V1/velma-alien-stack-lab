from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .computational_atlas_types import stable_hash


@dataclass(frozen=True)
class Milestone:
    index: int
    operation: str
    operand: int
    expected_state: int


@dataclass(frozen=True)
class HorizonJob:
    job_id: str
    horizon: int
    initial_state: int
    milestones: tuple[Milestone, ...]
    seed: int


def _step(state: int, operation: str, operand: int) -> int:
    if operation == "add":
        return state + operand
    if operation == "mul":
        return state * operand
    if operation == "sub":
        return state - operand
    raise ValueError(operation)


def build_horizon_jobs(seed: int = 20260915) -> list[HorizonJob]:
    jobs: list[HorizonJob] = []
    horizons = (8, 16, 32, 64)
    for horizon in horizons:
        for slot in range(10):
            state = 1 + ((seed + horizon + slot) % 7)
            initial = state
            milestones: list[Milestone] = []
            for index in range(horizon):
                operation = ("add", "mul", "sub")[(seed + slot + index) % 3]
                operand = 1 + ((seed // 7 + slot * 3 + index) % 3)
                # Keep the deterministic state bounded while preserving exact sequential dependence.
                if operation == "mul" and abs(state) > 100000:
                    operation = "sub"
                state = _step(state, operation, operand)
                milestones.append(Milestone(index=index, operation=operation, operand=operand, expected_state=state))
            jobs.append(HorizonJob(
                job_id=f"HZ-{seed}-{horizon}-{slot:02d}-{stable_hash([seed, horizon, slot])[:8]}",
                horizon=horizon,
                initial_state=initial,
                milestones=tuple(milestones),
                seed=seed,
            ))
    return jobs


def execute_horizon_job(job: HorizonJob, *, authoritative_verifier: bool, injected_states: dict[int, int] | None = None) -> dict[str, Any]:
    injected_states = injected_states or {}
    state = job.initial_state
    first_error: int | None = None
    detected_at: int | None = None
    correct = 0
    trace: list[dict[str, Any]] = []
    for milestone in job.milestones:
        state = _step(state, milestone.operation, milestone.operand)
        if milestone.index in injected_states:
            state = injected_states[milestone.index]
        is_correct = state == milestone.expected_state
        correct += int(is_correct)
        if not is_correct and first_error is None:
            first_error = milestone.index
        if authoritative_verifier and not is_correct and detected_at is None:
            detected_at = milestone.index
        trace.append({"index": milestone.index, "state": state, "expected": milestone.expected_state, "correct": is_correct})
    verified = first_error is None
    return {
        "verified": verified,
        "milestones_correct": correct,
        "milestones_total": job.horizon,
        "first_error": first_error,
        "detected_at": detected_at,
        "silent_wrong_milestones": 0 if authoritative_verifier else job.horizon - correct,
        "trace": trace,
    }
