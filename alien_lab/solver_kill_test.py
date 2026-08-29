from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .architecture_discovery import build_task, execute_plan


SOLVABLE_FAMILIES = (
    "linear_dependency",
    "conditional_branch",
    "multi_record_join",
    "loop_worklist",
    "policy_guard",
    "composition",
    "drift_resolution",
)
SOLVABLE_STAGES = ("NOVEL", "PARAMETER_VARIATION", "DRIFT", "COMPOSITION", "TRANSFER")
DIFFICULTIES = (12, 16, 20, 24, 28, 32)
UNSEEN_SEEDS = tuple(range(20260901, 20260917))
LABEL_RE = re.compile(r"^action=(\S+) requires=(\S+) condition=(\S+)$")
TARGET_SOLVABLE_RATE = 2381 / 2548
WILSON_GATE = 0.9345


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = successes / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return max(0.0, center - half), min(1.0, center + half)


@dataclass(frozen=True)
class ParsedNode:
    action_id: str
    predecessor: str
    condition: str
    locator: str
    slot: int
    forbidden: bool


@dataclass(frozen=True)
class SolverResult:
    ok: bool
    locators: tuple[str, ...]
    derivation: tuple[dict[str, Any], ...]
    error: str | None = None


def _condition_matches(condition: str, public_flag: int) -> tuple[bool | None, str | None]:
    if condition == "any":
        return True, None
    match = re.fullmatch(r"flag=(\d+)", condition)
    if not match:
        return None, f"UNSUPPORTED_CONDITION:{condition}"
    return int(match.group(1)) == int(public_flag), None


def solve_public_task(public_task: dict[str, Any]) -> SolverResult:
    """Solve one 008 task using only its public representation.

    No TaskSpec, oracle state, required semantic sequence, model output, memory,
    or previously solved trace is accepted by this interface.
    """
    if not isinstance(public_task, dict):
        return SolverResult(False, (), (), "PUBLIC_TASK_NOT_OBJECT")
    surface = public_task.get("surface")
    if not isinstance(surface, list) or not surface:
        return SolverResult(False, (), (), "PUBLIC_SURFACE_MISSING")
    try:
        public_flag = int(public_task.get("public_flag"))
    except (TypeError, ValueError):
        return SolverResult(False, (), (), "PUBLIC_FLAG_INVALID")

    nodes: list[ParsedNode] = []
    derivation: list[dict[str, Any]] = []
    semantic_ids: set[str] = set()
    locators: set[str] = set()

    for raw in surface:
        if not isinstance(raw, dict):
            return SolverResult(False, (), tuple(derivation), "SURFACE_ROW_NOT_OBJECT")
        locator = raw.get("locator")
        label = raw.get("label")
        if not isinstance(locator, str) or not locator:
            return SolverResult(False, (), tuple(derivation), "LOCATOR_INVALID")
        if locator in locators:
            return SolverResult(False, (), tuple(derivation), f"DUPLICATE_LOCATOR:{locator}")
        locators.add(locator)
        if not isinstance(label, str):
            return SolverResult(False, (), tuple(derivation), f"MALFORMED_LABEL:{locator}")
        match = LABEL_RE.fullmatch(label)
        if not match:
            return SolverResult(False, (), tuple(derivation), f"MALFORMED_LABEL:{locator}")
        action_id, predecessor, condition = match.groups()
        if action_id in semantic_ids:
            return SolverResult(False, (), tuple(derivation), f"DUPLICATE_ACTION:{action_id}")
        semantic_ids.add(action_id)
        try:
            slot = int(raw.get("slot"))
        except (TypeError, ValueError):
            return SolverResult(False, (), tuple(derivation), f"SLOT_INVALID:{locator}")
        forbidden = bool(raw.get("forbidden", False))
        node = ParsedNode(action_id, predecessor, condition, locator, slot, forbidden)
        nodes.append(node)
        derivation.append({
            "action_id": action_id,
            "predecessor": predecessor,
            "condition": condition,
            "locator": locator,
            "slot": slot,
            "forbidden": forbidden,
            "included": False,
            "reason": "UNCLASSIFIED",
        })

    eligible: list[ParsedNode] = []
    for idx, node in enumerate(nodes):
        row = derivation[idx]
        if node.forbidden:
            row["reason"] = "FORBIDDEN"
            continue
        if node.predecessor == "NEVER":
            row["reason"] = "NEVER_DISTRACTOR"
            continue
        condition_ok, condition_error = _condition_matches(node.condition, public_flag)
        if condition_error:
            return SolverResult(False, (), tuple(derivation), condition_error)
        if not condition_ok:
            row["reason"] = "CONDITION_FALSE"
            continue
        row["reason"] = "ELIGIBLE"
        eligible.append(node)

    if not eligible:
        return SolverResult(False, (), tuple(derivation), "NO_ELIGIBLE_ACTIONS")

    eligible_ids = {node.action_id for node in eligible}
    for node in eligible:
        if node.predecessor != "START" and node.predecessor not in eligible_ids:
            return SolverResult(
                False,
                (),
                tuple(derivation),
                f"MISSING_PREDECESSOR:{node.action_id}:{node.predecessor}",
            )

    successors: dict[str, list[ParsedNode]] = {}
    for node in eligible:
        successors.setdefault(node.predecessor, []).append(node)
    for rows in successors.values():
        rows.sort(key=lambda node: (node.slot, node.action_id, node.locator))

    root_rows = successors.get("START", [])
    if not root_rows:
        return SolverResult(False, (), tuple(derivation), "NO_SUCCESSOR:START")
    if len(root_rows) != 1:
        return SolverResult(False, (), tuple(derivation), "AMBIGUOUS_SUCCESSOR:START")

    visited: set[str] = set()
    ordered: list[ParsedNode] = []
    predecessor = "START"
    while True:
        candidates = successors.get(predecessor, [])
        if not candidates:
            break
        if len(candidates) != 1:
            return SolverResult(False, (), tuple(derivation), f"AMBIGUOUS_SUCCESSOR:{predecessor}")
        node = candidates[0]
        if node.action_id in visited:
            return SolverResult(False, (), tuple(derivation), f"CYCLE:{node.action_id}")
        visited.add(node.action_id)
        ordered.append(node)
        predecessor = node.action_id

    if visited != eligible_ids:
        disconnected = ",".join(sorted(eligible_ids - visited))
        return SolverResult(False, (), tuple(derivation), f"DISCONNECTED_ELIGIBLE:{disconnected}")

    included = {node.action_id for node in ordered}
    for row in derivation:
        if row["action_id"] in included:
            row["included"] = True
            row["reason"] = "PATH"

    return SolverResult(True, tuple(node.locator for node in ordered), tuple(derivation), None)


@dataclass(frozen=True)
class KillCell:
    cell_id: str
    order: int
    phase: str
    seed: int
    family: str
    difficulty: int
    stage: str
    lineage: str
    task_id: str


@dataclass(frozen=True)
class KillEvidence:
    cell_id: str
    order: int
    phase: str
    seed: int
    family: str
    difficulty: int
    stage: str
    lineage: str
    task_id: str
    task_public: dict[str, Any]
    oracle_hash: str
    solver_ok: bool
    solver_error: str | None
    solver_locators: tuple[str, ...]
    solver_derivation: tuple[dict[str, Any], ...]
    executed_semantics: tuple[str, ...]
    screen_success: bool | None
    authoritative_success: bool | None
    verified_success: bool | None
    classification: str
    model_calls: int
    valid_evidence: bool
    error: str | None


def default_config() -> dict[str, Any]:
    return {
        "experiment_id": "009-solver-kill-test",
        "solvable_count": 64,
        "silent_control_count": 16,
        "unseen_seeds": list(UNSEEN_SEEDS),
        "solvable_families": list(SOLVABLE_FAMILIES),
        "solvable_stages": list(SOLVABLE_STAGES),
        "difficulties": list(DIFFICULTIES),
    }


def _validated_sequence(config: dict[str, Any], key: str, fallback: tuple[Any, ...]) -> tuple[Any, ...]:
    raw = config.get(key, list(fallback))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"CONFIG_INVALID:{key}")
    return tuple(raw)


def build_kill_ledger(config: dict[str, Any]) -> list[KillCell]:
    try:
        solvable_count = int(config.get("solvable_count", 64))
        silent_count = int(config.get("silent_control_count", 16))
    except (TypeError, ValueError) as exc:
        raise ValueError("CONFIG_INVALID:counts") from exc
    if solvable_count < 1 or silent_count < 0:
        raise ValueError("CONFIG_INVALID:counts")

    seeds = tuple(int(x) for x in _validated_sequence(config, "unseen_seeds", UNSEEN_SEEDS))
    if any(seed in {20260829, 20260830} for seed in seeds):
        raise ValueError("CONFIG_INVALID:008_SEED_REUSE")
    families = tuple(str(x) for x in _validated_sequence(config, "solvable_families", SOLVABLE_FAMILIES))
    if any(f not in SOLVABLE_FAMILIES for f in families):
        raise ValueError("CONFIG_INVALID:solvable_families")
    stages = tuple(str(x) for x in _validated_sequence(config, "solvable_stages", SOLVABLE_STAGES))
    if any(stage == "SILENT_EFFECT_FAULT" for stage in stages):
        raise ValueError("CONFIG_INVALID:solvable_stages")
    difficulties = tuple(int(x) for x in _validated_sequence(config, "difficulties", DIFFICULTIES))
    if any(diff <= 0 for diff in difficulties):
        raise ValueError("CONFIG_INVALID:difficulties")

    cells: list[KillCell] = []
    order = 0

    def add(phase: str, seed: int, family: str, difficulty: int, stage: str, lineage: str) -> None:
        nonlocal order
        task = build_task(seed, family, difficulty, stage, lineage)
        cell_id = stable_hash([phase, seed, family, difficulty, stage, lineage, task.task_id])[:24]
        cells.append(KillCell(cell_id, order, phase, seed, family, difficulty, stage, lineage, task.task_id))
        order += 1

    for i in range(solvable_count):
        family = families[i % len(families)]
        stage = stages[(i // len(families)) % len(stages)]
        difficulty = difficulties[(i * 5 + i // len(families)) % len(difficulties)]
        seed = seeds[i % len(seeds)]
        add("SOLVABLE_KILL", seed, family, difficulty, stage, f"009-K-{i:03d}")

    for i in range(silent_count):
        seed = seeds[(i + 3) % len(seeds)]
        difficulty = difficulties[(i * 3 + 1) % len(difficulties)]
        if i % 2 == 0:
            family = "silent_effect_fault"
            stage = SOLVABLE_STAGES[i % len(SOLVABLE_STAGES)]
        else:
            family = families[i % len(families)]
            stage = "SILENT_EFFECT_FAULT"
        add("SILENT_CONTROL", seed, family, difficulty, stage, f"009-S-{i:03d}")

    if len({cell.cell_id for cell in cells}) != len(cells):
        raise RuntimeError("LEDGER_CELL_ID_COLLISION")
    return cells


def _run_cell(cell: KillCell) -> KillEvidence:
    task = build_task(cell.seed, cell.family, cell.difficulty, cell.stage, cell.lineage)
    if task.task_id != cell.task_id:
        return KillEvidence(
            cell.cell_id, cell.order, cell.phase, cell.seed, cell.family, cell.difficulty,
            cell.stage, cell.lineage, cell.task_id, task.public_dict(), task.oracle_hash,
            False, "TASK_ID_MISMATCH", (), (), (), None, None, None,
            "INVALID_HARNESS", 0, False, "TASK_ID_MISMATCH",
        )

    public_task = task.public_dict()
    result = solve_public_task(public_task)
    if not result.ok:
        classification = "SOLVER_FAILURE" if cell.phase == "SOLVABLE_KILL" else "SILENT_CONTROL_FAILURE"
        return KillEvidence(
            cell.cell_id, cell.order, cell.phase, cell.seed, cell.family, cell.difficulty,
            cell.stage, cell.lineage, cell.task_id, public_task, task.oracle_hash,
            False, result.error, result.locators, result.derivation, (), False, False, False,
            classification, 0, True, result.error,
        )

    public_locators = {row["locator"] for row in public_task["surface"]}
    if any(locator not in public_locators for locator in result.locators):
        return KillEvidence(
            cell.cell_id, cell.order, cell.phase, cell.seed, cell.family, cell.difficulty,
            cell.stage, cell.lineage, cell.task_id, public_task, task.oracle_hash,
            True, None, result.locators, result.derivation, (), None, None, None,
            "INVALID_HARNESS", 0, False, "SOLVER_EMITTED_NONPUBLIC_LOCATOR",
        )

    outcome = execute_plan(task, list(result.locators))
    if cell.phase == "SOLVABLE_KILL":
        classification = "SOLVER_SUCCESS" if outcome.verified_success else "SOLVER_FAILURE"
    else:
        expected_refutation = bool(
            outcome.screen_success is True
            and outcome.authoritative_success is False
            and outcome.verified_success is False
        )
        classification = "EXPECTED_REFUTATION" if expected_refutation else "SILENT_CONTROL_FAILURE"

    return KillEvidence(
        cell.cell_id, cell.order, cell.phase, cell.seed, cell.family, cell.difficulty,
        cell.stage, cell.lineage, cell.task_id, public_task, task.oracle_hash,
        True, None, result.locators, result.derivation, tuple(outcome.semantics),
        outcome.screen_success, outcome.authoritative_success, outcome.verified_success,
        classification, 0, True, outcome.error,
    )


def _write_evidence(root: Path, evidence: KillEvidence) -> None:
    payload = asdict(evidence)
    atomic_json(root / "cells" / f"{evidence.cell_id}.json", {
        "evidence": payload,
        "sha256": stable_hash(payload),
    })


def run_experiment(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    ledger = build_kill_ledger(config)
    ledger_payload = [asdict(cell) for cell in ledger]
    ledger_hash = stable_hash(ledger_payload)
    manifest_path = output_dir / "ledger-manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("ledger_hash") != ledger_hash:
            raise RuntimeError("OUTPUT_DIRECTORY_LEDGER_MISMATCH")

    atomic_json(output_dir / "ledger.json", ledger_payload)
    atomic_json(manifest_path, {
        "experiment_id": config.get("experiment_id", "009-solver-kill-test"),
        "ledger_hash": ledger_hash,
        "expected_cells": len(ledger),
        "solver_input_contract": "TaskSpec.public_dict() only",
        "model_calls_allowed": 0,
    })

    evidence: list[KillEvidence] = []
    for cell in ledger:
        try:
            ev = _run_cell(cell)
        except Exception as exc:
            task = build_task(cell.seed, cell.family, cell.difficulty, cell.stage, cell.lineage)
            ev = KillEvidence(
                cell.cell_id, cell.order, cell.phase, cell.seed, cell.family, cell.difficulty,
                cell.stage, cell.lineage, cell.task_id, task.public_dict(), task.oracle_hash,
                False, None, (), (), (), None, None, None,
                "INVALID_HARNESS", 0, False, repr(exc),
            )
        _write_evidence(output_dir, ev)
        evidence.append(ev)

    solvable = [ev for ev in evidence if ev.phase == "SOLVABLE_KILL"]
    controls = [ev for ev in evidence if ev.phase == "SILENT_CONTROL"]
    successes = sum(ev.classification == "SOLVER_SUCCESS" for ev in solvable)
    failures = len(solvable) - successes
    controls_refuted = sum(ev.classification == "EXPECTED_REFUTATION" for ev in controls)
    invalid = sum(not ev.valid_evidence for ev in evidence)
    model_calls = sum(ev.model_calls for ev in evidence)
    lower, upper = wilson(successes, len(solvable))
    replay_payload = [
        {
            "cell_id": ev.cell_id,
            "classification": ev.classification,
            "solver_locators": ev.solver_locators,
            "solver_derivation": ev.solver_derivation,
            "verified_success": ev.verified_success,
        }
        for ev in evidence
    ]
    replay_fingerprint = stable_hash(replay_payload)

    passed = bool(
        len(solvable) == 64
        and successes == 64
        and len(controls) == 16
        and controls_refuted == 16
        and invalid == 0
        and model_calls == 0
        and lower is not None
        and lower > WILSON_GATE
    )

    summary = {
        "experiment_id": config.get("experiment_id", "009-solver-kill-test"),
        "expected_cells": len(ledger),
        "terminal_cells": len(evidence),
        "solvable_total": len(solvable),
        "solvable_successes": successes,
        "solvable_failures": failures,
        "solvable_success_rate": successes / len(solvable) if solvable else None,
        "target_full_workload_success_rate": 0.80,
        "required_solvable_success_rate": TARGET_SOLVABLE_RATE,
        "wilson95_lower": lower,
        "wilson95_upper": upper,
        "silent_control_total": len(controls),
        "silent_controls_correctly_refuted": controls_refuted,
        "invalid_cells": invalid,
        "model_calls": model_calls,
        "replay_fingerprint": replay_fingerprint,
        "ledger_hash": ledger_hash,
        "solver_kill_test_passed": passed,
        "conclusion": "PASS_SOLVER_HYPOTHESIS" if passed else "KILL_OR_NOT_YET_PROVEN",
    }
    atomic_json(output_dir / "summary.json", summary)
    return summary


def load_config(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("CONFIG_INVALID:root")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 009 deterministic solver kill test")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", default="results/009-solver-kill-test")
    args = parser.parse_args(argv)
    try:
        config = load_config(Path(args.config))
        summary = run_experiment(config, Path(args.output_dir))
    except Exception as exc:
        print(json.dumps({"solver_kill_test_passed": False, "invalid": True, "error": repr(exc)}, indent=2))
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["solver_kill_test_passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
