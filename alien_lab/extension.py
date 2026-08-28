from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

from .design import PRIMITIVES, all_subsets, subset_id
from .experiment import ExperimentConfig, ExperimentRunner
from .ollama import OllamaClient
from .records import stable_hash
from .taskgen import generate_taskset, write_sealed_taskset


def _prior_p95_seconds(prior_results_dir: Path, prior_summary: dict[str, Any]) -> float:
    walls: list[float] = []
    runs_path = prior_results_dir / "runs.jsonl"
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            wall_ms = float(row.get("wall_ms", 0.0))
            if row.get("status") == "OK" and wall_ms > 0:
                walls.append(wall_ms / 1000.0)
    if walls:
        walls.sort()
        return walls[max(0, math.ceil(0.95 * len(walls)) - 1)]
    generations = max(1, int(prior_summary.get("generation_count", 0)))
    return max(0.001, float(prior_summary.get("elapsed_seconds", 0.0)) / generations)


def _validate_prior(config: ExperimentConfig, prior_results_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    summary_path = prior_results_dir / "summary.json"
    environment_path = prior_results_dir / "environment.json"
    if not summary_path.exists() or not environment_path.exists():
        raise RuntimeError("prior results must contain summary.json and environment.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    if not summary.get("discovery_analysis"):
        raise RuntimeError("prior results do not contain discovery_analysis")
    prior_cfg = environment.get("config", {})
    for field in ("model", "quantization", "context_limit"):
        if prior_cfg.get(field) != getattr(config, field):
            raise RuntimeError(
                f"prior {field}={prior_cfg.get(field)!r} does not match extension {field}={getattr(config, field)!r}"
            )
    return summary, environment


def run_extension(
    config: ExperimentConfig,
    *,
    prior_results_dir: Path,
    client: OllamaClient,
    output_dir: Path | None = None,
    clock=time.monotonic,
) -> ExperimentRunner:
    prior_results_dir = Path(prior_results_dir)
    prior_summary, prior_environment = _validate_prior(config, prior_results_dir)
    prior_elapsed = float(prior_summary.get("elapsed_seconds", 0.0))
    remaining_target = max(0.0, config.target_minutes * 60.0 - prior_elapsed)
    remaining_ceiling = max(0.0, config.ceiling_minutes * 60.0 - prior_elapsed)
    if remaining_ceiling <= 0:
        raise RuntimeError("prior run already consumed the configured cumulative ceiling")

    out = output_dir or Path("results") / config.experiment_id
    runner = ExperimentRunner(config, client=client, clock=clock, output_dir=out)
    runner.output_dir.mkdir(parents=True, exist_ok=True)
    if (runner.output_dir / "runs.jsonl").exists() or (runner.output_dir / "observations.jsonl").exists():
        raise RuntimeError(
            f"output directory already contains raw run evidence: {runner.output_dir}. Use a new output directory."
        )

    runner._write_environment_snapshot()
    public, sealed = generate_taskset(config.seed)
    runner._sealed = sealed.answers
    write_sealed_taskset(
        public, sealed, runner.output_dir / "tasks.public.json", runner.output_dir / "sealed" / "answers.json"
    )

    prior_p95 = _prior_p95_seconds(prior_results_dir, prior_summary)
    prior_context = {
        "prior_results_dir": str(prior_results_dir),
        "prior_experiment_id": prior_summary.get("experiment_id"),
        "prior_summary_hash": stable_hash(prior_summary),
        "prior_environment_hash": stable_hash(prior_environment),
        "prior_elapsed_seconds": prior_elapsed,
        "prior_generation_count": int(prior_summary.get("generation_count", 0)),
        "prior_observation_count": int(prior_summary.get("observation_count", 0)),
        "prior_total_prompt_tokens": int(prior_summary.get("total_prompt_tokens", 0)),
        "prior_total_eval_tokens": int(prior_summary.get("total_eval_tokens", 0)),
        "prior_duration_p95_seconds": prior_p95,
        "remaining_target_seconds_at_start": remaining_target,
        "remaining_ceiling_seconds_at_start": remaining_ceiling,
    }
    (runner.output_dir / "prior_evidence.json").write_text(
        json.dumps(prior_context, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    runner._started = clock()
    runner._deadline = runner._started + remaining_ceiling
    target_deadline = runner._started + remaining_target
    analysis = prior_summary["discovery_analysis"]

    def duration_estimate() -> float:
        walls = sorted(r.wall_ms / 1000.0 for r in runner.records if r.status == "OK" and r.wall_ms > 0)
        if not walls:
            return prior_p95
        return walls[max(0, math.ceil(0.95 * len(walls)) - 1)]

    def target_remaining() -> float:
        return max(0.0, target_deadline - clock())

    def can_start(calls: int = 1) -> bool:
        needed = calls * duration_estimate() + config.safety_margin_seconds
        return target_remaining() > needed and runner._remaining() > needed

    full = frozenset(PRIMITIVES)
    empty = frozenset()
    block_index = 0

    while can_start(65):
        if block_index == 0:
            tasks = list(public.transfer)
            evaluator = runner._sealed
            taskset_seed = config.seed
            split = "transfer"
        else:
            taskset_seed = config.seed + 1000 + block_index
            variant, variant_sealed = generate_taskset(taskset_seed)
            evaluator = variant_sealed.answers
            if block_index % 2:
                tasks = list(variant.discovery)
                split = "discovery"
            else:
                tasks = list(variant.transfer)
                split = "transfer"

        conditions: list[tuple[str, frozenset[str], tuple[str, ...], str]] = [
            ("RAW", empty, (), "raw")
        ]
        for subset in all_subsets():
            rep = "STRUCTURED" if not subset else "COMPOUND"
            order = tuple(p for p in PRIMITIVES if p in subset)
            conditions.append((rep, subset, order, subset_id(subset)))

        completed = 0
        for rep, subset, order, label in conditions:
            ok = runner._execute_packet(
                tasks=tasks,
                phase="adaptive_cube",
                representation=rep,
                subset=subset,
                order=order,
                budget=config.discovery_budget,
                tag=f"adaptive-cube:{block_index}:{split}:{label}",
                taskset_seed=taskset_seed,
                evaluator_override=evaluator,
            )
            if not ok:
                break
            completed += 1
        if completed != 65:
            break
        block_index += 1

    winner = frozenset(analysis.get("minimal_subset") or analysis.get("best_subset") or PRIMITIVES)
    positive = frozenset(analysis.get("strongest_positive_pair") or ())
    negative = frozenset(analysis.get("strongest_negative_pair") or ())
    tail_conditions: list[tuple[str, frozenset[str], int, str]] = [
        ("RAW", empty, 0, "raw"),
        ("STRUCTURED", empty, 0, "structured"),
        ("COMPOUND", winner, 0, "winner"),
        ("COMPOUND", full, 0, "full"),
        ("FUSED_COMPOUND", winner or full, 1, "winner-fusion"),
        ("RECURSIVE_COMPOUND", full, 2, "full-recursive"),
    ]
    if positive:
        tail_conditions.append(("COMPOUND", positive, 0, "positive-pair"))
    if negative:
        tail_conditions.append(("COMPOUND", negative, 0, "negative-pair"))

    tail_index = 0
    while can_start(1):
        taskset_seed = config.seed + 5000 + tail_index
        variant, variant_sealed = generate_taskset(taskset_seed)
        tasks = list(variant.transfer if tail_index % 2 == 0 else variant.discovery)
        rep, subset, fusion_depth, label = tail_conditions[tail_index % len(tail_conditions)]
        order = tuple(p for p in PRIMITIVES if p in subset)
        ok = runner._execute_packet(
            tasks=tasks,
            phase="adaptive_tail",
            representation=rep,
            subset=subset,
            order=order,
            budget=config.discovery_budget,
            tag=f"adaptive-tail:{tail_index}:{label}",
            taskset_seed=taskset_seed,
            evaluator_override=variant_sealed.answers,
            fusion_depth=fusion_depth,
        )
        if not ok:
            break
        tail_index += 1

    runner._finish(discovery_analysis=analysis)
    extension_elapsed = float(runner.summary.get("elapsed_seconds", 0.0))
    cumulative = {
        "prior_context": prior_context,
        "extension_elapsed_seconds": extension_elapsed,
        "cumulative_elapsed_seconds": prior_elapsed + extension_elapsed,
        "extension_generation_count": len(runner.records),
        "cumulative_generation_count": prior_context["prior_generation_count"] + len(runner.records),
        "extension_observation_count": len(runner.observations),
        "cumulative_observation_count": prior_context["prior_observation_count"] + len(runner.observations),
        "extension_total_prompt_tokens": runner.summary.get("total_prompt_tokens", 0),
        "extension_total_eval_tokens": runner.summary.get("total_eval_tokens", 0),
        "cumulative_total_prompt_tokens": prior_context["prior_total_prompt_tokens"] + runner.summary.get("total_prompt_tokens", 0),
        "cumulative_total_eval_tokens": prior_context["prior_total_eval_tokens"] + runner.summary.get("total_eval_tokens", 0),
        "adaptive_cube_generations": sum(1 for r in runner.records if r.phase == "adaptive_cube"),
        "adaptive_tail_generations": sum(1 for r in runner.records if r.phase == "adaptive_tail"),
        "target_minutes": config.target_minutes,
        "ceiling_minutes": config.ceiling_minutes,
    }
    runner.summary["extension"] = cumulative
    (runner.output_dir / "summary.json").write_text(
        json.dumps(runner.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (runner.output_dir / "extension_summary.json").write_text(
        json.dumps(cumulative, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (runner.output_dir / "report.md").open("a", encoding="utf-8") as fh:
        fh.write("\n## Cumulative Extension\n\n")
        fh.write(f"- Prior elapsed: {prior_elapsed:.2f}s\n")
        fh.write(f"- Extension elapsed: {extension_elapsed:.2f}s\n")
        fh.write(f"- Cumulative elapsed: {cumulative['cumulative_elapsed_seconds']:.2f}s\n")
        fh.write(f"- New adaptive-cube generations: {cumulative['adaptive_cube_generations']}\n")
        fh.write(f"- New adaptive-tail generations: {cumulative['adaptive_tail_generations']}\n")
    return runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extend a frozen VELMA alien-stack experiment to its cumulative time target")
    parser.add_argument("--config", required=True)
    parser.add_argument("--extend-from", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    config = ExperimentConfig.from_json(Path(args.config))
    client = OllamaClient(config.ollama_url)
    runner = run_extension(
        config,
        prior_results_dir=Path(args.extend_from),
        client=client,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(runner.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
