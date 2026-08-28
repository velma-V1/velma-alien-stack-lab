from __future__ import annotations

import argparse
import json
import random
from itertools import permutations
from pathlib import Path
from typing import Any

from .compiler import compile_workspace
from .design import PRIMITIVES
from .experiment import ExperimentConfig
from .ollama import OllamaClient
from .order_effects import (
    CANONICAL_ORDER,
    CANDIDATE_ORDER,
    ControlledSeedClient,
    _edge,
    _make_task,
    _src,
)
from .scoring_repair import ScoringRepairRunner, StrictFinalAnswerClient
from .types import Task, Workspace


FRONTIER_LEVELS = (1, 2, 3, 4, 5)
FRONTIER_REPLICATION_OFFSETS = (0, 1, 2, 3)
FRONTIER_ORDERS = (CANONICAL_ORDER, CANDIDATE_ORDER)


def _active_chain(prefix: str, entry: str, terminal: str, depth: int, scope: str):
    if depth < 1:
        raise ValueError("depth must be >= 1")
    nodes = [entry]
    for i in range(1, depth):
        nodes.append(f"{prefix}_hop_{i}")
    nodes.append(terminal)
    edges = []
    for i, (source, target) in enumerate(zip(nodes, nodes[1:]), 1):
        edges.append(_edge(f"{prefix}_a{i}", source, target, True, scope))
    for i in range(1, depth + 1):
        branch_source = nodes[min(i - 1, len(nodes) - 2)]
        edges.append(_edge(f"{prefix}_d{i}", branch_source, f"{prefix}_dead_{i}", False, scope))
    return nodes, edges


def _noise_sources(prefix: str, count: int, *, target_key: str, start_authority: int = 6):
    out = []
    for i in range(count):
        if i % 3 == 0:
            key = target_key
            value = f"decoy_{i}"
        else:
            key = f"noise_key_{i}"
            value = f"noise_value_{i}"
        out.append(_src(
            f"{prefix}-noise-{i}",
            key,
            value,
            start_authority + (i % 4),
            40 + i,
            f"{prefix}_noise_scope_{i}",
        ))
    return out


def _expected(
    *,
    active_path: list[str],
    current_state: dict[str, str],
    required_evidence: list[str],
    forbidden_evidence: list[str],
    target_key: str,
    contradiction_values: list[str] | None = None,
    memory_transitions: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "active_path": list(active_path),
        "current_state": dict(current_state),
        "required_evidence": sorted(required_evidence),
        "forbidden_evidence": sorted(forbidden_evidence),
        "target_key": target_key,
        "contradiction_values": sorted(contradiction_values or []),
        "memory_transitions": [list(x) for x in (memory_transitions or [])],
    }


def build_frontier_tasks(
    seed: int,
    level: int,
) -> tuple[tuple[Task, ...], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if level not in FRONTIER_LEVELS:
        raise ValueError(f"level must be one of {FRONTIER_LEVELS}")
    rng = random.Random(seed)
    tasks: list[Task] = []
    sealed: dict[str, dict[str, Any]] = {}
    expected: dict[str, dict[str, Any]] = {}

    depth = level + 1
    noise_count = level * 3

    # 1. Active-path scoped evidence must survive long enough for STATE to use it.
    path1, edges1 = _active_chain("fps", "ingress", "live_writer", depth, "delivery")
    sources1 = [
        _src("fps-live", "mode", "strict", 5, 5, "live_writer"),
        _src("fps-fallback", "mode", "compat", 2, 9, "delivery"),
        *_noise_sources("fps", noise_count, target_key="mode", start_authority=7),
    ]
    task, ans = _make_task(
        rng,
        task_id=f"frontier-path-state-L{level}",
        family="frontier_path_state",
        target_scope="delivery",
        target_key="mode",
        entry="ingress",
        sources=sources1,
        edges=edges1,
        procedure_rules=[
            "Use current state that belongs to the active production path or requested scope.",
            "Do not use discarded or inactive-path evidence as production state.",
        ],
        question="Which mode should the active live_writer use?",
        correct="Use strict in live_writer.",
        distractors=["Use compat in live_writer.", "Use decoy_0 in live_writer.", "Patch the inactive path to strict."],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path1,
        current_state={"mode": "strict"},
        required_evidence=["fps-live", "fps-fallback"],
        forbidden_evidence=[s.record_id for s in sources1 if s.record_id.startswith("fps-noise-")],
        target_key="mode",
    )

    # 2. An irrelevant equal-rank conflict should not become target uncertainty.
    path2, edges2 = _active_chain("fsc", "collector", "exporter", depth, "telemetry")
    conflict_authority = 10 + level
    sources2 = [
        _src("fsc-current", "format", "otel", 5, 7, "telemetry"),
        _src("fsc-old", "format", "legacy", 5, 6, "telemetry"),
        _src("fsc-conflict-a", "format", "json", conflict_authority, 50, "search"),
        _src("fsc-conflict-b", "format", "binary", conflict_authority, 50, "search"),
        *_noise_sources("fsc", noise_count, target_key="noise_format", start_authority=6),
    ]
    task, ans = _make_task(
        rng,
        task_id=f"frontier-scope-conflict-L{level}",
        family="frontier_scope_conflict",
        target_scope="telemetry",
        target_key="format",
        entry="collector",
        sources=sources2,
        edges=edges2,
        procedure_rules=[
            "Escalate only unresolved contradictions that remain relevant to the requested production scope.",
            "Otherwise apply the compiled current state to the active path.",
        ],
        question="What should the active exporter do?",
        correct="Use otel in exporter.",
        distractors=["Escalate telemetry as unresolved.", "Use json in exporter.", "Use binary in exporter."],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path2,
        current_state={"format": "otel"},
        required_evidence=["fsc-current", "fsc-old"],
        forbidden_evidence=["fsc-conflict-a", "fsc-conflict-b"] + [s.record_id for s in sources2 if s.record_id.startswith("fsc-noise-")],
        target_key="format",
    )

    # 3. Deep but relevant history; both good orders should preserve it.
    path3, edges3 = _active_chain("fh", "worker", "customer_writer", depth, "customer")
    history_values = ["account_id", "customer_id", "party_id"]
    for i in range(3, level + 3):
        history_values.append(f"party_id_v{i}")
    history_sources = [
        _src(f"fh-r{i+1}", "column", value, 5, i + 1, "customer")
        for i, value in enumerate(history_values)
    ]
    sources3 = [
        *history_sources,
        *_noise_sources("fh", noise_count, target_key="other_column", start_authority=7),
    ]
    final_column = history_values[-1]
    task, ans = _make_task(
        rng,
        task_id=f"frontier-history-L{level}",
        family="frontier_history",
        target_scope="customer",
        target_key="column",
        entry="worker",
        sources=sources3,
        edges=edges3,
        procedure_rules=["Migrate the active writer to the latest resolved authoritative state."],
        question="Which customer_writer migration is justified now?",
        correct=f"Migrate customer_writer to {final_column}.",
        distractors=[
            f"Migrate customer_writer to {history_values[-2]}.",
            "Migrate customer_writer to account_id.",
            "Use an unrelated noise column.",
        ],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path3,
        current_state={"column": final_column},
        required_evidence=[s.record_id for s in history_sources],
        forbidden_evidence=[s.record_id for s in sources3 if s.record_id.startswith("fh-noise-")],
        target_key="column",
        memory_transitions=list(zip(history_values, history_values[1:])),
    )

    # 4. Target state is buried among many unrelated keys and higher-authority cross-scope poison.
    path4, edges4 = _active_chain("fmk", "auth", "control", depth, "identity")
    sources4 = [
        _src("fmk-current", "role", "operator", 6, 9, "identity"),
        _src("fmk-old", "role", "viewer", 6, 8, "identity"),
        _src("fmk-poison", "role", "billing_admin", 12 + level, 70, "billing"),
    ]
    for i in range(level * 2):
        sources4.append(_src(
            f"fmk-related-{i}",
            f"identity_key_{i}",
            f"identity_value_{i}",
            6 + (i % 2),
            10 + i,
            "identity",
        ))
    sources4.extend(_noise_sources("fmk", noise_count, target_key="role", start_authority=8))
    task, ans = _make_task(
        rng,
        task_id=f"frontier-multi-key-L{level}",
        family="frontier_multi_key",
        target_scope="identity",
        target_key="role",
        entry="auth",
        sources=sources4,
        edges=edges4,
        procedure_rules=[
            "Resolve the requested key independently from unrelated keys.",
            "Apply only the relevant current value to the active production path.",
        ],
        question="Which role should the active control path require?",
        correct="Require operator in control.",
        distractors=["Require viewer in control.", "Require billing_admin in control.", "Use identity_value_0 as the role."],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path4,
        current_state={"role": "operator"},
        required_evidence=["fmk-current", "fmk-old"] + [f"fmk-related-{i}" for i in range(level * 2)],
        forbidden_evidence=["fmk-poison"] + [s.record_id for s in sources4 if s.record_id.startswith("fmk-noise-")],
        target_key="role",
    )

    # 5. Relevant evidence lives on a terminal path-node scope, not the declared target scope.
    path5, edges5 = _active_chain("fpsc", "router", "commit_handler", depth, "payments")
    sources5 = [
        _src("fpsc-live", "approval", "three_person", 7, 12, "commit_handler"),
        _src("fpsc-scope-old", "approval", "two_person", 4, 11, "payments"),
        _src("fpsc-poison", "approval", "automatic", 15 + level, 90, "analytics"),
        *_noise_sources("fpsc", noise_count, target_key="approval", start_authority=9),
    ]
    task, ans = _make_task(
        rng,
        task_id=f"frontier-path-scope-L{level}",
        family="frontier_path_scope",
        target_scope="payments",
        target_key="approval",
        entry="router",
        sources=sources5,
        edges=edges5,
        procedure_rules=[
            "Path-scoped policy on the active terminal is relevant to the production decision.",
            "Out-of-scope policy must not override active-path policy.",
        ],
        question="Which approval rule should commit_handler enforce?",
        correct="Require three-person approval in commit_handler.",
        distractors=[
            "Require two-person approval in commit_handler.",
            "Allow automatic approval in commit_handler.",
            "Apply three-person approval only to an inactive branch.",
        ],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path5,
        current_state={"approval": "three_person"},
        required_evidence=["fpsc-live", "fpsc-scope-old"],
        forbidden_evidence=["fpsc-poison"] + [s.record_id for s in sources5 if s.record_id.startswith("fpsc-noise-")],
        target_key="approval",
    )

    # 6. Compound case: relevant revision chain plus irrelevant high-rank conflict and extra keys.
    path6, edges6 = _active_chain("fc", "scheduler", "executor", depth, "jobs")
    sources6 = [
        _src("fc-r1", "retry_mode", "bounded", 6, 1, "jobs"),
        _src("fc-r2", "retry_mode", "adaptive", 6, 2, "jobs"),
        _src("fc-conflict-a", "retry_mode", "instant", 14 + level, 99, "ui"),
        _src("fc-conflict-b", "retry_mode", "disabled", 14 + level, 99, "ui"),
    ]
    for i in range(level * 2):
        sources6.append(_src(
            f"fc-job-key-{i}",
            f"job_key_{i}",
            f"job_value_{i}",
            5,
            20 + i,
            "jobs",
        ))
    sources6.extend(_noise_sources("fc", noise_count, target_key="retry_mode", start_authority=9))
    task, ans = _make_task(
        rng,
        task_id=f"frontier-compound-L{level}",
        family="frontier_compound",
        target_scope="jobs",
        target_key="retry_mode",
        entry="scheduler",
        sources=sources6,
        edges=edges6,
        procedure_rules=[
            "Ignore contradictions outside the requested production scope.",
            "Use the latest resolved relevant state and its authoritative transition on the active path.",
        ],
        question="Which retry configuration is justified for executor?",
        correct="Use adaptive in executor.",
        distractors=["Escalate jobs as unresolved.", "Use instant in executor.", "Use disabled in executor."],
    )
    tasks.append(task); sealed[task.task_id] = ans
    expected[task.task_id] = _expected(
        active_path=path6,
        current_state={"retry_mode": "adaptive"},
        required_evidence=["fc-r1", "fc-r2"] + [f"fc-job-key-{i}" for i in range(level * 2)],
        forbidden_evidence=["fc-conflict-a", "fc-conflict-b"] + [s.record_id for s in sources6 if s.record_id.startswith("fc-noise-")],
        target_key="retry_mode",
        memory_transitions=[("bounded", "adaptive")],
    )

    return tuple(tasks), sealed, expected


def score_workspace(ws: Workspace, expected: dict[str, Any]) -> dict[str, Any]:
    path_ok = list(ws.active_path) == list(expected["active_path"])
    state_ok = all(ws.current_state.get(key) == value for key, value in expected["current_state"].items())

    target_key = expected["target_key"]
    actual_conflicts = []
    for item in ws.contradictions:
        if item.get("key") == target_key:
            actual_conflicts.extend(str(v) for v in item.get("values", []))
    uncertainty_ok = sorted(set(actual_conflicts)) == sorted(expected["contradiction_values"])

    required = set(expected["required_evidence"])
    forbidden = set(expected["forbidden_evidence"])
    visible = set(ws.evidence_ids)
    relevance_ok = required.issubset(visible) and not (forbidden & visible)

    expected_transitions = [tuple(x) for x in expected["memory_transitions"]]
    if expected_transitions:
        actual_transitions = [
            (str(item.get("from")), str(item.get("to")))
            for item in ws.memory_deltas
            if item.get("key") == target_key
        ]
        memory_ok = actual_transitions == expected_transitions
    else:
        memory_ok = True

    overall = path_ok and state_ok and uncertainty_ok and relevance_ok and memory_ok
    return {
        "path": path_ok,
        "state": state_ok,
        "uncertainty": uncertainty_ok,
        "relevance": relevance_ok,
        "memory": memory_ok,
        "overall": overall,
    }


def deterministic_permutation_scan(
    tasks: tuple[Task, ...] | list[Task],
    expected: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    full = tuple(PRIMITIVES)
    rows = []
    for order in permutations(PRIMITIVES):
        component_hits = {key: 0 for key in ("path", "state", "uncertainty", "relevance", "memory", "overall")}
        for task in tasks:
            ws = compile_workspace(task.compiler_view(), full, order=order)
            score = score_workspace(ws, expected[task.task_id])
            for key in component_hits:
                component_hits[key] += int(score[key])
        count = len(tasks)
        row = {
            "order": list(order),
            "task_count": count,
            **{f"{key}_accuracy": component_hits[key] / count if count else 0.0 for key in component_hits},
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            -row["overall_accuracy"],
            -row["state_accuracy"],
            -row["uncertainty_accuracy"],
            -row["relevance_accuracy"],
            -row["memory_accuracy"],
            row["order"],
        )
    )
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return {"permutation_count": len(rows), "rows": rows}


def _aggregate_neural(runner: ScoringRepairRunner) -> dict[str, Any]:
    per_level = []
    packet_scores: dict[str, dict[str, float]] = {}

    for level in FRONTIER_LEVELS:
        phase = f"frontier_level_{level}"
        level_obs = [o for o in runner.observations if o["phase"] == phase]
        level_rows = {}
        for label, order in (("canonical", CANONICAL_ORDER), ("candidate", CANDIDATE_ORDER)):
            items = [o for o in level_obs if tuple(o.get("pass_order", [])) == order]
            scored = [o for o in items if o.get("verified_success") is not None]
            level_rows[label] = {
                "accuracy": sum(bool(o["verified_success"]) for o in scored) / len(scored) if scored else None,
                "scored_observations": len(scored),
            }
        per_level.append({"level": level, **level_rows})

        seeds = sorted({str(o.get("taskset_seed")) for o in level_obs})
        for seed in seeds:
            key = f"L{level}:{seed}"
            packet_scores[key] = {}
            seed_obs = [o for o in level_obs if str(o.get("taskset_seed")) == seed]
            for label, order in (("canonical", CANONICAL_ORDER), ("candidate", CANDIDATE_ORDER)):
                vals = [
                    bool(o["verified_success"])
                    for o in seed_obs
                    if tuple(o.get("pass_order", [])) == order and o.get("verified_success") is not None
                ]
                packet_scores[key][label] = sum(vals) / len(vals) if vals else 0.0

    overall = {}
    for label, order in (("canonical", CANONICAL_ORDER), ("candidate", CANDIDATE_ORDER)):
        items = [
            o for o in runner.observations
            if o["phase"].startswith("frontier_level_")
            and tuple(o.get("pass_order", [])) == order
            and o.get("verified_success") is not None
        ]
        overall[label] = {
            "accuracy": sum(bool(o["verified_success"]) for o in items) / len(items) if items else None,
            "scored_observations": len(items),
        }

    wins = sum(v.get("candidate", -1.0) > v.get("canonical", -1.0) for v in packet_scores.values())
    losses = sum(v.get("candidate", -1.0) < v.get("canonical", -1.0) for v in packet_scores.values())
    first_advantage = next(
        (row["level"] for row in per_level if row["candidate"]["accuracy"] > row["canonical"]["accuracy"]),
        None,
    )

    def first_error(label: str):
        return next((row["level"] for row in per_level if row[label]["accuracy"] < 1.0), None)

    expected_per_order_level = len(FRONTIER_REPLICATION_OFFSETS) * 6
    expected_generations = len(FRONTIER_LEVELS) * len(FRONTIER_REPLICATION_OFFSETS) * len(FRONTIER_ORDERS)
    capability_valid = (
        len(runner.records) == expected_generations
        and all(r.status == "OK" for r in runner.records)
        and all(
            row[label]["scored_observations"] == expected_per_order_level
            for row in per_level
            for label in ("canonical", "candidate")
        )
    )
    return {
        "capability_valid": capability_valid,
        "thinking_enabled": False,
        "expected_generations": expected_generations,
        "generation_count": len(runner.records),
        "observation_count": len(runner.observations),
        "per_level": per_level,
        "overall": overall,
        "packet_scores": packet_scores,
        "candidate_packet_wins": wins,
        "candidate_packet_losses": losses,
        "first_candidate_advantage_level": first_advantage,
        "canonical_first_error_level": first_error("canonical"),
        "candidate_first_error_level": first_error("candidate"),
        "discriminating_level_present": any(
            row["candidate"]["accuracy"] != row["canonical"]["accuracy"] for row in per_level
        ),
    }


def _write_report(out: Path, summary: dict[str, Any]) -> None:
    neural = summary["frontier_analysis"]
    det = summary["compiler_analysis"]
    lines = [
        "# Experiment 006 — Capability Frontier",
        "",
        f"- Capability valid: {neural['capability_valid']}",
        f"- Preflight passed: {summary['preflight_passed']}",
        f"- Candidate extends neural frontier: {summary['candidate_frontier_supported']}",
        f"- Deterministic candidate overall accuracy: {det['candidate']['overall_accuracy']:.4f}",
        f"- Deterministic canonical overall accuracy: {det['canonical']['overall_accuracy']:.4f}",
        f"- Candidate packet wins/losses: {neural['candidate_packet_wins']}/{neural['candidate_packet_losses']}",
        "",
        "## Neural accuracy by difficulty",
        "",
    ]
    for row in neural["per_level"]:
        lines.append(
            f"- L{row['level']}: candidate={row['candidate']['accuracy']:.4f}, "
            f"canonical={row['canonical']['accuracy']:.4f}"
        )
    lines.extend([
        "",
        "## Deterministic compiler ranking",
        "",
        f"- Candidate rank: {det['candidate']['rank']}/720",
        f"- Canonical rank: {det['canonical']['rank']}/720",
    ])
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_frontier_experiment(config: ExperimentConfig, *, output_dir: Path | None = None) -> dict[str, Any]:
    out = output_dir or Path("results") / config.experiment_id
    out.mkdir(parents=True, exist_ok=True)
    if (out / "runs.jsonl").exists() or (out / "observations.jsonl").exists():
        raise RuntimeError(f"output directory already contains raw run evidence: {out}")

    strict = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    client = ControlledSeedClient(strict)
    runner = ScoringRepairRunner(config, client=client, output_dir=out)
    runner._write_environment_snapshot()

    preflight = runner.preflight()
    (out / "preflight.json").write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not preflight["passed"]:
        raise RuntimeError("scoring preflight failed; capability frontier did not start")

    # Score the compiler itself across all 720 orders before invoking the model.
    scan_tasks: list[Task] = []
    scan_expected: dict[str, dict[str, Any]] = {}
    complexity_manifest = []
    for level in FRONTIER_LEVELS:
        tasks, _, expected = build_frontier_tasks(config.seed + 50000 + level, level)
        scan_tasks.extend(tasks)
        scan_expected.update(expected)
        complexity_manifest.append({
            "level": level,
            "task_count": len(tasks),
            "source_count": sum(len(t.sources) for t in tasks),
            "edge_count": sum(len(t.edges) for t in tasks),
        })
    permutation_scan = deterministic_permutation_scan(scan_tasks, scan_expected)
    (out / "deterministic_permutation_scan.json").write_text(
        json.dumps(permutation_scan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    by_order = {tuple(row["order"]): row for row in permutation_scan["rows"]}
    compiler_analysis = {
        "permutation_count": permutation_scan["permutation_count"],
        "candidate": by_order[CANDIDATE_ORDER],
        "canonical": by_order[CANONICAL_ORDER],
        "top_10": permutation_scan["rows"][:10],
        "complexity_manifest": complexity_manifest,
    }

    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0
    full = frozenset(PRIMITIVES)
    aborted = False

    for level in FRONTIER_LEVELS:
        for offset in FRONTIER_REPLICATION_OFFSETS:
            taskset_seed = config.seed + level * 1000 + offset
            model_seed = config.seed + 20000 + level * 100 + offset
            tasks, sealed, _ = build_frontier_tasks(taskset_seed, level)
            client.seed_override = model_seed
            for label, order in (("canonical", CANONICAL_ORDER), ("candidate", CANDIDATE_ORDER)):
                completed = runner._execute_packet(
                    tasks=list(tasks),
                    phase=f"frontier_level_{level}",
                    representation="COMPOUND",
                    subset=full,
                    order=order,
                    budget=config.discovery_budget,
                    tag=f"L{level}:{offset}:{label}",
                    taskset_seed=taskset_seed,
                    evaluator_override=sealed,
                )
                if not completed:
                    aborted = True
                    break
            if aborted:
                break
        if aborted:
            break

    client.seed_override = None
    frontier_analysis = _aggregate_neural(runner)

    deterministic_advantage = (
        compiler_analysis["candidate"]["overall_accuracy"]
        > compiler_analysis["canonical"]["overall_accuracy"]
    )
    neural_advantage = (
        frontier_analysis["overall"]["candidate"]["accuracy"] is not None
        and frontier_analysis["overall"]["canonical"]["accuracy"] is not None
        and frontier_analysis["overall"]["candidate"]["accuracy"]
        > frontier_analysis["overall"]["canonical"]["accuracy"]
        and frontier_analysis["candidate_packet_wins"] > frontier_analysis["candidate_packet_losses"]
    )
    candidate_frontier_supported = (
        frontier_analysis["capability_valid"]
        and deterministic_advantage
        and neural_advantage
    )

    summary = {
        "experiment_id": config.experiment_id,
        "preflight_passed": preflight["passed"],
        "compiler_analysis": compiler_analysis,
        "frontier_analysis": frontier_analysis,
        "candidate_frontier_supported": candidate_frontier_supported,
        "interpretation": (
            "CANDIDATE_EXTENDS_FRONTIER"
            if candidate_frontier_supported
            else "FRONTIER_ADVANTAGE_NOT_ESTABLISHED"
        ),
        "total_prompt_tokens": sum(r.prompt_tokens for r in runner.records),
        "total_eval_tokens": sum(r.eval_tokens for r in runner.records),
        "total_compiler_ms": sum(r.compiler_ms for r in runner.records),
        "time_budget_aborts": sum(r.status == "TIME_BUDGET_ABORT" for r in runner.records),
        "unscorable_generations": sum(r.status == "UNSCORABLE" for r in runner.records),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(out, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure where compiler ordering changes Qwen's capability frontier"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    config = ExperimentConfig.from_json(Path(args.config))
    summary = run_frontier_experiment(
        config,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["frontier_analysis"]["capability_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
