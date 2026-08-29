from __future__ import annotations

from dataclasses import dataclass

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
    """Build the frozen Phase H job definition only.

    Runtime long-horizon execution/recovery/verifier behavior is intentionally
    absent until the explicit post-evidence H gate.
    """
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
