from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

from .compiler import compile_workspace
from .design import PRIMITIVES
from .experiment import ExperimentConfig
from .ollama import OllamaClient
from .scoring_repair import ScoringRepairRunner, StrictFinalAnswerClient
from .types import Edge, SourceRecord, Task, Workspace


CANONICAL_ORDER = tuple(PRIMITIVES)
CANDIDATE_ORDER = ("path", "relevance", "state", "uncertainty", "memory", "procedure")
REPLICATION_OFFSETS = (0, 1, 2, 3)


def order_catalog() -> tuple[tuple[str, ...], ...]:
    candidates = [
        CANONICAL_ORDER,
        CANDIDATE_ORDER,
        tuple(reversed(CANDIDATE_ORDER)),
        ("relevance", "path", "state", "uncertainty", "memory", "procedure"),
        ("path", "state", "relevance", "uncertainty", "memory", "procedure"),
        ("path", "uncertainty", "relevance", "state", "memory", "procedure"),
        ("path", "memory", "relevance", "state", "uncertainty", "procedure"),
        ("procedure", "path", "relevance", "state", "uncertainty", "memory"),
        ("path", "relevance", "memory", "uncertainty", "state", "procedure"),
    ]
    out: list[tuple[str, ...]] = []
    for order in candidates:
        if order not in out:
            out.append(order)
    return tuple(out)


def _src(record_id: str, key: str, value: str, authority: int, revision: int, scope: str) -> SourceRecord:
    return SourceRecord(
        record_id=record_id,
        key=key,
        value=value,
        authority=authority,
        revision=revision,
        scope=scope,
        raw=f"{record_id} [{scope}] authority={authority} revision={revision}: {key}={value}",
    )


def _edge(edge_id: str, source: str, target: str, active: bool, scope: str) -> Edge:
    state = "active" if active else "inactive"
    return Edge(edge_id, source, target, active, scope, f"{edge_id}: {source}->{target} is {state} [{scope}]")


def _make_task(
    rng: random.Random,
    *,
    task_id: str,
    family: str,
    target_scope: str,
    target_key: str,
    entry: str,
    sources: list[SourceRecord],
    edges: list[Edge],
    procedure_rules: list[str],
    question: str,
    correct: str,
    distractors: list[str],
) -> tuple[Task, dict[str, Any]]:
    options = [correct, *distractors]
    rng.shuffle(options)
    choices = {letter: option for letter, option in zip("ABCD", options)}
    answer = next(letter for letter, value in choices.items() if value == correct)
    rng.shuffle(sources)
    rng.shuffle(edges)
    task = Task(
        task_id=task_id,
        family=family,
        target_scope=target_scope,
        target_key=target_key,
        entry=entry,
        sources=tuple(sources),
        edges=tuple(edges),
        procedure_rules=tuple(procedure_rules),
        question=question,
        choices=choices,
    )
    return task, {"answer": answer, "correct_action": correct, "deterministic_unique": True}


def build_order_stress_tasks(seed: int) -> tuple[tuple[Task, ...], dict[str, dict[str, Any]]]:
    rng = random.Random(seed)
    tasks: list[Task] = []
    sealed: dict[str, dict[str, Any]] = {}

    specs = [
        dict(
            task_id="order-path-relevance-01",
            family="order_path_relevance",
            target_scope="routing",
            target_key="mode",
            entry="router",
            sources=[
                _src("live-policy", "mode", "active", 4, 2, "live_handler"),
                _src("routing-fallback", "mode", "stale", 2, 9, "routing"),
                _src("archive-noise", "mode", "archive", 9, 99, "archive"),
            ],
            edges=[
                _edge("opr1", "router", "live_handler", True, "routing"),
                _edge("opr2", "router", "legacy_handler", False, "routing"),
            ],
            procedure_rules=[
                "Use the compiled current state for the active production path.",
                "Do not infer production state from inactive or discarded evidence.",
            ],
            question="Which action follows the compiled active-path state?",
            correct="Use active in live_handler.",
            distractors=["Use stale in live_handler.", "Use archive in live_handler.", "Patch legacy_handler to active."],
        ),
        dict(
            task_id="order-relevance-state-02",
            family="order_relevance_state",
            target_scope="payments",
            target_key="mode",
            entry="gateway",
            sources=[
                _src("payment-policy", "mode", "safe", 3, 5, "payments"),
                _src("analytics-policy", "mode", "turbo", 9, 9, "analytics"),
                _src("payment-old", "mode", "legacy", 3, 4, "payments"),
            ],
            edges=[_edge("ors1", "gateway", "charge_handler", True, "payments")],
            procedure_rules=["Apply the compiled current state to the requested production scope."],
            question="Which mode should the payments path use?",
            correct="Use safe in charge_handler.",
            distractors=["Use turbo in charge_handler.", "Use legacy in charge_handler.", "Escalate because no state can be selected."],
        ),
        dict(
            task_id="order-relevance-uncertainty-03",
            family="order_relevance_uncertainty",
            target_scope="payments",
            target_key="mode",
            entry="gateway",
            sources=[
                _src("payment-current", "mode", "safe", 3, 5, "payments"),
                _src("analytics-a", "mode", "turbo", 9, 9, "analytics"),
                _src("analytics-b", "mode", "eco", 9, 9, "analytics"),
            ],
            edges=[_edge("oru1", "gateway", "charge_handler", True, "payments")],
            procedure_rules=[
                "If the compiled workspace contains an unresolved contradiction for the requested key, make no change and escalate.",
                "Otherwise apply the compiled current state.",
            ],
            question="What action is justified for the payments mode?",
            correct="Use safe in charge_handler.",
            distractors=["Escalate the payments mode as unresolved.", "Use turbo in charge_handler.", "Use eco in charge_handler."],
        ),
        dict(
            task_id="order-relevance-memory-04",
            family="order_relevance_memory",
            target_scope="customer",
            target_key="column",
            entry="worker",
            sources=[
                _src("customer-r1", "column", "legacy", 3, 1, "customer"),
                _src("customer-r2", "column", "current", 3, 2, "customer"),
                _src("analytics-r1", "column", "shadow_old", 9, 1, "analytics"),
                _src("analytics-r2", "column", "shadow_new", 9, 2, "analytics"),
            ],
            edges=[_edge("orm1", "worker", "customer_writer", True, "customer")],
            procedure_rules=["Apply the compiled authoritative transition for the requested production scope."],
            question="Which migration is justified for customer_writer?",
            correct="Migrate customer_writer from legacy to current.",
            distractors=[
                "Migrate customer_writer from shadow_old to shadow_new.",
                "Keep customer_writer on legacy.",
                "Migrate customer_writer from current to legacy.",
            ],
        ),
    ]

    for spec in specs:
        task, answer = _make_task(rng, **spec)
        tasks.append(task)
        sealed[task.task_id] = answer
    return tuple(tasks), sealed


def semantic_workspace_signature(ws: Workspace) -> str:
    payload = {
        "evidence_ids": sorted(ws.evidence_ids),
        "edge_ids": sorted(ws.edge_ids),
        "current_state": dict(sorted(ws.current_state.items())),
        "active_path": list(ws.active_path),
        "contradictions": sorted(ws.contradictions, key=lambda x: json.dumps(x, sort_keys=True)),
        "procedure": list(ws.procedure),
        "memory_deltas": sorted(ws.memory_deltas, key=lambda x: json.dumps(x, sort_keys=True)),
        "fused_relations": sorted(ws.fused_relations, key=lambda x: json.dumps(x, sort_keys=True)),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _order_label(order: tuple[str, ...]) -> str:
    if order == CANONICAL_ORDER:
        return "canonical"
    if order == CANDIDATE_ORDER:
        return "candidate"
    return "->".join(order)


def _analyze(runner: ScoringRepairRunner, workspace_matrix: list[dict[str, Any]]) -> dict[str, Any]:
    orders = order_catalog()
    observations = [o for o in runner.observations if o["phase"] == "order_effect"]
    per_order = []
    for order in orders:
        label = _order_label(order)
        items = [o for o in observations if o.get("metadata_order_label") == label]
        scored = [o for o in items if o.get("verified_success") is not None]
        accuracy = sum(bool(o["verified_success"]) for o in scored) / len(scored) if scored else None
        run_ids = {o["run_id"] for o in items}
        runs = [r for r in runner.records if r.run_id in run_ids]
        per_order.append({
            "label": label,
            "order": list(order),
            "accuracy": accuracy,
            "scored_observations": len(scored),
            "avg_eval_tokens": (sum(r.eval_tokens for r in runs) / len(runs)) if runs else None,
            "avg_wall_ms": (sum(r.wall_ms for r in runs) / len(runs)) if runs else None,
        })

    # _execute_packet does not know our human-readable order label, so recover it
    # from pass_order and patch aggregates directly from observations.
    by_order = {}
    for row in per_order:
        by_order[tuple(row["order"])] = row
        row["scored_observations"] = 0
        row["accuracy"] = None
    counts: dict[tuple[str, ...], list[bool]] = {tuple(x["order"]): [] for x in per_order}
    for obs in observations:
        key = tuple(obs.get("pass_order", []))
        if obs.get("verified_success") is not None and key in counts:
            counts[key].append(bool(obs["verified_success"]))
    for key, vals in counts.items():
        row = by_order[key]
        row["scored_observations"] = len(vals)
        row["accuracy"] = (sum(vals) / len(vals)) if vals else None

    per_order.sort(key=lambda x: (-(x["accuracy"] if x["accuracy"] is not None else -1), x["label"]))
    canonical = next(x for x in per_order if x["label"] == "canonical")
    candidate = next(x for x in per_order if x["label"] == "candidate")

    task_classes: dict[str, set[str]] = {}
    for item in workspace_matrix:
        task_classes.setdefault(item["task_family"], set()).add(item["semantic_signature"])

    replication_scores: dict[str, dict[str, float]] = {}
    for obs in observations:
        if obs.get("verified_success") is None:
            continue
        seed = str(obs.get("taskset_seed"))
        label = _order_label(tuple(obs.get("pass_order", [])))
        replication_scores.setdefault(seed, {}).setdefault(label, 0.0)
    for seed, labels in replication_scores.items():
        for label in list(labels):
            vals = [
                bool(o["verified_success"])
                for o in observations
                if str(o.get("taskset_seed")) == seed
                and _order_label(tuple(o.get("pass_order", []))) == label
                and o.get("verified_success") is not None
            ]
            labels[label] = sum(vals) / len(vals) if vals else 0.0

    best = per_order[0]
    better_reps = sum(
        scores.get(best["label"], 0.0) > scores.get("canonical", 0.0)
        for scores in replication_scores.values()
    )
    semantic_sensitive = {family: len(sigs) for family, sigs in sorted(task_classes.items())}
    capability_valid = all(r.status == "OK" for r in runner.records) and all(
        x["scored_observations"] == len(REPLICATION_OFFSETS) * 4 for x in per_order
    )
    return {
        "capability_valid": capability_valid,
        "thinking_enabled": False,
        "replications": len(REPLICATION_OFFSETS),
        "order_count": len(orders),
        "generation_count": len(runner.records),
        "observation_count": len(observations),
        "canonical": canonical,
        "candidate": candidate,
        "best_order": best,
        "best_beats_canonical_in_replications": better_reps,
        "semantic_workspace_classes_by_task_family": semantic_sensitive,
        "semantic_order_effect_present": any(count > 1 for count in semantic_sensitive.values()),
        "per_order": per_order,
        "replication_scores": replication_scores,
    }


def run_order_experiment(config: ExperimentConfig, *, output_dir: Path | None = None) -> dict[str, Any]:
    out = output_dir or Path("results") / config.experiment_id
    out.mkdir(parents=True, exist_ok=True)
    if (out / "runs.jsonl").exists() or (out / "observations.jsonl").exists():
        raise RuntimeError(f"output directory already contains raw run evidence: {out}")

    client = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    runner = ScoringRepairRunner(config, client=client, output_dir=out)
    runner._write_environment_snapshot()
    preflight = runner.preflight()
    (out / "preflight.json").write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not preflight["passed"]:
        raise RuntimeError("scoring preflight failed; order experiment did not start")

    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0
    workspace_matrix: list[dict[str, Any]] = []
    full = frozenset(PRIMITIVES)

    for offset in REPLICATION_OFFSETS:
        taskset_seed = config.seed + 100 + offset
        tasks, sealed = build_order_stress_tasks(taskset_seed)
        for order in order_catalog():
            for task in tasks:
                ws = compile_workspace(task.compiler_view(), tuple(PRIMITIVES), order=order)
                workspace_matrix.append({
                    "taskset_seed": taskset_seed,
                    "task_id": task.task_id,
                    "task_family": task.family,
                    "order": list(order),
                    "order_label": _order_label(order),
                    "semantic_signature": semantic_workspace_signature(ws),
                })
            completed = runner._execute_packet(
                tasks=list(tasks),
                phase="order_effect",
                representation="COMPOUND",
                subset=full,
                order=order,
                budget=config.discovery_budget,
                tag=f"order:{offset}:{_order_label(order)}",
                taskset_seed=taskset_seed,
                evaluator_override=sealed,
            )
            if not completed:
                break
        if runner.records and runner.records[-1].status != "OK":
            break

    (out / "workspace_matrix.json").write_text(
        json.dumps(workspace_matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    analysis = _analyze(runner, workspace_matrix)
    summary = {
        "experiment_id": config.experiment_id,
        "elapsed_seconds": runner.clock() - runner._started,
        "preflight_passed": preflight["passed"],
        "order_analysis": analysis,
        "total_prompt_tokens": sum(r.prompt_tokens for r in runner.records),
        "total_eval_tokens": sum(r.eval_tokens for r in runner.records),
        "total_compiler_ms": sum(r.compiler_ms for r in runner.records),
        "time_budget_aborts": sum(r.status == "TIME_BUDGET_ABORT" for r in runner.records),
        "unscorable_generations": sum(r.status == "UNSCORABLE" for r in runner.records),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure causal pass-order effects in the VELMA alien stack")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    config = ExperimentConfig.from_json(Path(args.config))
    summary = run_order_experiment(config, output_dir=Path(args.output_dir) if args.output_dir else None)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["order_analysis"]["capability_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
