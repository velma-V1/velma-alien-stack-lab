from __future__ import annotations

import argparse
import json
import random
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
    semantic_workspace_signature,
)
from .scoring_repair import ScoringRepairRunner, StrictFinalAnswerClient
from .taskgen import generate_taskset
from .types import Task


HELDOUT_REPLICATION_OFFSETS = (0, 1, 2, 3, 4, 5)
LEGACY_REPLICATION_OFFSETS = (0, 1)
REVERSE_CANDIDATE_ORDER = tuple(reversed(CANDIDATE_ORDER))
RELEVANCE_FIRST_ORDER = ("relevance", "path", "state", "uncertainty", "memory", "procedure")


def transfer_order_catalog() -> tuple[tuple[str, ...], ...]:
    """Four pre-registered full-stack orders for held-out transfer."""
    return (
        CANONICAL_ORDER,
        CANDIDATE_ORDER,
        REVERSE_CANDIDATE_ORDER,
        RELEVANCE_FIRST_ORDER,
    )


def _order_label(order: tuple[str, ...]) -> str:
    if order == CANONICAL_ORDER:
        return "canonical"
    if order == CANDIDATE_ORDER:
        return "candidate"
    if order == REVERSE_CANDIDATE_ORDER:
        return "reverse-candidate"
    if order == RELEVANCE_FIRST_ORDER:
        return "relevance-first"
    return "->".join(order)


def build_heldout_transfer_tasks(seed: int) -> tuple[tuple[Task, ...], dict[str, dict[str, Any]]]:
    """Six mixed-structure tasks that were not used to select Experiment 004's winner.

    Three tasks contain genuine order-sensitive scope/path interactions and three
    are deliberately broader non-specialized controls. Source and answer order
    are reshuffled by seed while the causal truth remains fixed.
    """
    rng = random.Random(seed)
    tasks: list[Task] = []
    sealed: dict[str, dict[str, Any]] = {}

    specs = [
        dict(
            task_id="heldout-multihop-policy-01",
            family="heldout_multihop_policy",
            target_scope="delivery",
            target_key="mode",
            entry="ingress",
            sources=[
                _src("writer-policy", "mode", "strict", 5, 4, "writer"),
                _src("delivery-fallback", "mode", "compat", 2, 8, "delivery"),
                _src("archive-policy", "mode", "archive", 9, 99, "archive"),
            ],
            edges=[
                _edge("hm1", "ingress", "router", True, "delivery"),
                _edge("hm2", "router", "writer", True, "delivery"),
                _edge("hm3", "router", "old_writer", False, "delivery"),
            ],
            procedure_rules=[
                "Use state belonging to the active production path and requested scope.",
                "Do not use discarded or inactive-path evidence as production state.",
            ],
            question="Which mode should the active writer use?",
            correct="Use strict in writer.",
            distractors=["Use archive in writer.", "Use compat in writer.", "Patch old_writer to strict."],
        ),
        dict(
            task_id="heldout-scope-authority-02",
            family="heldout_scope_authority",
            target_scope="checkout",
            target_key="approval",
            entry="checkout",
            sources=[
                _src("checkout-current", "approval", "two_person", 4, 6, "checkout"),
                _src("checkout-old", "approval", "single", 4, 5, "checkout"),
                _src("warehouse-policy", "approval", "automatic", 10, 12, "warehouse"),
                _src("checkout-note", "retry", "bounded", 1, 30, "checkout"),
            ],
            edges=[_edge("ha1", "checkout", "payment_commit", True, "checkout")],
            procedure_rules=["Apply the current authoritative policy for the requested production scope."],
            question="Which approval policy should payment_commit enforce?",
            correct="Require two-person approval in payment_commit.",
            distractors=[
                "Allow automatic approval in payment_commit.",
                "Require single-person approval in payment_commit.",
                "Escalate because checkout has no current policy.",
            ],
        ),
        dict(
            task_id="heldout-cross-scope-conflict-03",
            family="heldout_cross_scope_conflict",
            target_scope="telemetry",
            target_key="format",
            entry="collector",
            sources=[
                _src("telemetry-current", "format", "otel", 4, 7, "telemetry"),
                _src("search-a", "format", "json", 9, 11, "search"),
                _src("search-b", "format", "binary", 9, 11, "search"),
                _src("telemetry-old", "format", "legacy", 4, 6, "telemetry"),
            ],
            edges=[_edge("hc1", "collector", "exporter", True, "telemetry")],
            procedure_rules=[
                "Escalate only unresolved contradictions that belong to the requested production scope.",
                "Otherwise use the compiled current state.",
            ],
            question="What should the active telemetry exporter do?",
            correct="Use otel in exporter.",
            distractors=[
                "Escalate telemetry as unresolved.",
                "Use json in exporter.",
                "Use binary in exporter.",
            ],
        ),
        dict(
            task_id="heldout-multi-key-04",
            family="heldout_multi_key",
            target_scope="identity",
            target_key="role",
            entry="auth",
            sources=[
                _src("role-current", "role", "operator", 5, 9, "identity"),
                _src("role-old", "role", "viewer", 5, 8, "identity"),
                _src("identity-timeout", "timeout", "30", 8, 50, "identity"),
                _src("billing-role", "role", "billing_admin", 2, 40, "billing"),
            ],
            edges=[_edge("hk1", "auth", "control", True, "identity")],
            procedure_rules=["Resolve the requested key independently from unrelated keys and apply it to the active path."],
            question="Which role should control require?",
            correct="Require operator in control.",
            distractors=["Require viewer in control.", "Require billing_admin in control.", "Use timeout 30 as the role."],
        ),
        dict(
            task_id="heldout-resolved-history-05",
            family="heldout_resolved_history",
            target_scope="customer",
            target_key="column",
            entry="worker",
            sources=[
                _src("customer-r1", "column", "account_id", 4, 1, "customer"),
                _src("customer-r2", "column", "customer_id", 4, 2, "customer"),
                _src("customer-r3", "column", "party_id", 4, 3, "customer"),
                _src("docs", "column", "user_id", 1, 20, "customer"),
            ],
            edges=[_edge("hh1", "worker", "customer_writer", True, "customer")],
            procedure_rules=["Migrate the active writer to the latest resolved authoritative state."],
            question="Which migration direction is justified now?",
            correct="Migrate customer_writer to party_id.",
            distractors=[
                "Migrate customer_writer to customer_id.",
                "Migrate customer_writer to account_id.",
                "Migrate customer_writer to user_id.",
            ],
        ),
        dict(
            task_id="heldout-active-side-effect-06",
            family="heldout_active_side_effect",
            target_scope="orders",
            target_key="delivery",
            entry="orders",
            sources=[
                _src("delivery-current", "delivery", "at_least_once", 4, 5, "orders"),
                _src("delivery-old", "delivery", "best_effort", 4, 4, "orders"),
                _src("effect", "operation_effect", "charges_card", 4, 3, "orders"),
            ],
            edges=[
                _edge("hs1", "orders", "charge", True, "orders"),
                _edge("hs2", "orders", "preview", False, "orders"),
            ],
            procedure_rules=[
                "At-least-once execution with an external charge side effect requires idempotency on the active operation.",
                "Do not modify inactive preview paths.",
            ],
            question="Which repair preserves the active side-effect safety property?",
            correct="Add idempotency to charge.",
            distractors=["Add idempotency only to preview.", "Run charge twice for verification.", "Keep charge unchanged."],
        ),
    ]

    for spec in specs:
        task, answer = _make_task(rng, **spec)
        tasks.append(task)
        sealed[task.task_id] = answer
    return tuple(tasks), sealed


def _aggregate_order_rows(runner: ScoringRepairRunner, phase: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    observations = [o for o in runner.observations if o["phase"] == phase]
    for order in transfer_order_catalog():
        items = [o for o in observations if tuple(o.get("pass_order", [])) == order]
        scored = [o for o in items if o.get("verified_success") is not None]
        run_ids = {o["run_id"] for o in items}
        runs = [r for r in runner.records if r.run_id in run_ids]
        rows.append({
            "label": _order_label(order),
            "order": list(order),
            "accuracy": (sum(bool(o["verified_success"]) for o in scored) / len(scored)) if scored else None,
            "scored_observations": len(scored),
            "avg_eval_tokens": (sum(r.eval_tokens for r in runs) / len(runs)) if runs else None,
            "avg_wall_ms": (sum(r.wall_ms for r in runs) / len(runs)) if runs else None,
        })
    rows.sort(key=lambda x: (-(x["accuracy"] if x["accuracy"] is not None else -1), x["label"]))
    return rows


def _replication_scores(runner: ScoringRepairRunner, phase: str) -> dict[str, dict[str, float]]:
    observations = [o for o in runner.observations if o["phase"] == phase]
    result: dict[str, dict[str, float]] = {}
    for seed in sorted({str(o.get("taskset_seed")) for o in observations}):
        seed_obs = [o for o in observations if str(o.get("taskset_seed")) == seed]
        result[seed] = {}
        for order in transfer_order_catalog():
            vals = [
                bool(o["verified_success"])
                for o in seed_obs
                if tuple(o.get("pass_order", [])) == order and o.get("verified_success") is not None
            ]
            if vals:
                result[seed][_order_label(order)] = sum(vals) / len(vals)
    return result


def _analyze(runner: ScoringRepairRunner, workspace_matrix: list[dict[str, Any]]) -> dict[str, Any]:
    heldout_rows = _aggregate_order_rows(runner, "heldout_order_transfer")
    legacy_rows = _aggregate_order_rows(runner, "legacy_order_nonregression")
    heldout_scores = _replication_scores(runner, "heldout_order_transfer")
    legacy_scores = _replication_scores(runner, "legacy_order_nonregression")

    heldout_by_label = {row["label"]: row for row in heldout_rows}
    legacy_by_label = {row["label"]: row for row in legacy_rows}
    candidate = heldout_by_label["candidate"]
    canonical = heldout_by_label["canonical"]

    candidate_wins = sum(
        scores.get("candidate", -1.0) > scores.get("canonical", -1.0)
        for scores in heldout_scores.values()
    )
    candidate_losses = sum(
        scores.get("candidate", -1.0) < scores.get("canonical", -1.0)
        for scores in heldout_scores.values()
    )

    semantic_classes: dict[str, set[str]] = {}
    for item in workspace_matrix:
        semantic_classes.setdefault(item["task_family"], set()).add(item["semantic_signature"])
    semantic_counts = {family: len(values) for family, values in sorted(semantic_classes.items())}

    expected_heldout_generations = len(HELDOUT_REPLICATION_OFFSETS) * len(transfer_order_catalog())
    expected_legacy_generations = len(LEGACY_REPLICATION_OFFSETS) * len(transfer_order_catalog())
    expected_generations = expected_heldout_generations + expected_legacy_generations
    expected_heldout_per_order = len(HELDOUT_REPLICATION_OFFSETS) * 6
    expected_legacy_per_order = len(LEGACY_REPLICATION_OFFSETS) * 6

    capability_valid = (
        len(runner.records) == expected_generations
        and all(r.status == "OK" for r in runner.records)
        and all(row["scored_observations"] == expected_heldout_per_order for row in heldout_rows)
        and all(row["scored_observations"] == expected_legacy_per_order for row in legacy_rows)
    )

    legacy_noninferior = (
        legacy_by_label["candidate"]["accuracy"] is not None
        and legacy_by_label["canonical"]["accuracy"] is not None
        and legacy_by_label["candidate"]["accuracy"] >= legacy_by_label["canonical"]["accuracy"]
    )
    heldout_improves = (
        candidate["accuracy"] is not None
        and canonical["accuracy"] is not None
        and candidate["accuracy"] > canonical["accuracy"]
    )
    transfer_supported = capability_valid and heldout_improves and candidate_wins >= 4 and legacy_noninferior

    return {
        "capability_valid": capability_valid,
        "thinking_enabled": False,
        "heldout_replications": len(HELDOUT_REPLICATION_OFFSETS),
        "legacy_replications": len(LEGACY_REPLICATION_OFFSETS),
        "order_count": len(transfer_order_catalog()),
        "expected_generations": expected_generations,
        "generation_count": len(runner.records),
        "observation_count": len(runner.observations),
        "candidate": candidate,
        "canonical": canonical,
        "heldout_order_ranking": heldout_rows,
        "legacy_order_ranking": legacy_rows,
        "heldout_replication_scores": heldout_scores,
        "legacy_replication_scores": legacy_scores,
        "candidate_beats_canonical_in_heldout_replications": candidate_wins,
        "candidate_loses_to_canonical_in_heldout_replications": candidate_losses,
        "legacy_noninferior": legacy_noninferior,
        "heldout_improves": heldout_improves,
        "semantic_workspace_classes_by_task_family": semantic_counts,
        "semantic_order_effect_present": any(count > 1 for count in semantic_counts.values()),
        "candidate_transfer_supported": transfer_supported,
        "promotion_recommendation": "PROMOTE_CANDIDATE_ORDER" if transfer_supported else "DO_NOT_PROMOTE",
    }


def _write_report(out: Path, summary: dict[str, Any]) -> None:
    analysis = summary["transfer_analysis"]
    lines = [
        "# Experiment 005 — Held-out Order Transfer",
        "",
        f"- Capability valid: {analysis['capability_valid']}",
        f"- Preflight passed: {summary['preflight_passed']}",
        f"- Candidate transfer supported: {analysis['candidate_transfer_supported']}",
        f"- Promotion recommendation: {analysis['promotion_recommendation']}",
        f"- Candidate held-out wins over canonical: {analysis['candidate_beats_canonical_in_heldout_replications']}/{analysis['heldout_replications']}",
        f"- Legacy non-inferior: {analysis['legacy_noninferior']}",
        "",
        "## Held-out ranking",
        "",
    ]
    for row in analysis["heldout_order_ranking"]:
        lines.append(
            f"- {row['label']}: accuracy={row['accuracy']:.4f}, "
            f"avg_eval_tokens={row['avg_eval_tokens']:.2f}, avg_wall_ms={row['avg_wall_ms']:.1f}"
        )
    lines.extend(["", "## Legacy non-regression ranking", ""])
    for row in analysis["legacy_order_ranking"]:
        lines.append(
            f"- {row['label']}: accuracy={row['accuracy']:.4f}, "
            f"avg_eval_tokens={row['avg_eval_tokens']:.2f}, avg_wall_ms={row['avg_wall_ms']:.1f}"
        )
    lines.extend(["", "## Semantic workspace classes", ""])
    for family, count in analysis["semantic_workspace_classes_by_task_family"].items():
        lines.append(f"- {family}: {count}")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_transfer_experiment(config: ExperimentConfig, *, output_dir: Path | None = None) -> dict[str, Any]:
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
        raise RuntimeError("scoring preflight failed; held-out order transfer did not start")

    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0
    full = frozenset(PRIMITIVES)
    workspace_matrix: list[dict[str, Any]] = []
    aborted = False

    for offset in HELDOUT_REPLICATION_OFFSETS:
        taskset_seed = config.seed + 2000 + offset
        model_seed = config.seed + 12000 + offset
        tasks, sealed = build_heldout_transfer_tasks(taskset_seed)
        client.seed_override = model_seed
        for order in transfer_order_catalog():
            for task in tasks:
                ws = compile_workspace(task.compiler_view(), tuple(PRIMITIVES), order=order)
                workspace_matrix.append({
                    "phase": "heldout_order_transfer",
                    "taskset_seed": taskset_seed,
                    "model_seed": model_seed,
                    "task_id": task.task_id,
                    "task_family": task.family,
                    "order": list(order),
                    "order_label": _order_label(order),
                    "semantic_signature": semantic_workspace_signature(ws),
                })
            completed = runner._execute_packet(
                tasks=list(tasks),
                phase="heldout_order_transfer",
                representation="COMPOUND",
                subset=full,
                order=order,
                budget=config.discovery_budget,
                tag=f"heldout:{offset}:{_order_label(order)}",
                taskset_seed=taskset_seed,
                evaluator_override=sealed,
            )
            if not completed:
                aborted = True
                break
        if aborted:
            break

    if not aborted:
        for offset in LEGACY_REPLICATION_OFFSETS:
            taskset_seed = config.seed + 3000 + offset
            model_seed = config.seed + 13000 + offset
            public, sealed_obj = generate_taskset(taskset_seed)
            tasks = list(public.transfer)
            client.seed_override = model_seed
            for order in transfer_order_catalog():
                completed = runner._execute_packet(
                    tasks=tasks,
                    phase="legacy_order_nonregression",
                    representation="COMPOUND",
                    subset=full,
                    order=order,
                    budget=config.discovery_budget,
                    tag=f"legacy:{offset}:{_order_label(order)}",
                    taskset_seed=taskset_seed,
                    evaluator_override=sealed_obj.answers,
                )
                if not completed:
                    aborted = True
                    break
            if aborted:
                break

    client.seed_override = None
    (out / "workspace_matrix.json").write_text(
        json.dumps(workspace_matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    analysis = _analyze(runner, workspace_matrix)
    summary = {
        "experiment_id": config.experiment_id,
        "elapsed_seconds": runner.clock() - runner._started,
        "preflight_passed": preflight["passed"],
        "transfer_analysis": analysis,
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
    parser = argparse.ArgumentParser(description="Validate Experiment 004 order effects on held-out task structures")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    config = ExperimentConfig.from_json(Path(args.config))
    summary = run_transfer_experiment(config, output_dir=Path(args.output_dir) if args.output_dir else None)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["transfer_analysis"]["capability_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
