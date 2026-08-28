from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import adaptive_memory_frontier as core
from . import adaptive_memory_frontier_safe as safe
from .experiment import ExperimentConfig
from .ollama import OllamaClient
from .scoring_repair import StrictFinalAnswerClient


# Twelve stages are enough to move from trivial three-rule composition to eighty dependent
# applications while still leaving room for the three matched arms and occasional confirmation.
# This is a preregistered schedule, not a performance-dependent difficulty change.
DEPTH_SCHEDULE = (3, 5, 8, 12, 17, 23, 30, 38, 47, 57, 68, 80)


def accelerated_depth(level: int) -> int:
    if level < 1:
        raise ValueError("level must be >= 1")
    if level <= len(DEPTH_SCHEDULE):
        return DEPTH_SCHEDULE[level - 1]
    # Not normally reached; keeps the function monotonic for defensive use.
    return DEPTH_SCHEDULE[-1] + 13 * (level - len(DEPTH_SCHEDULE))


def configure_accelerated_schedule() -> None:
    # `build_level_packet` and its selector resolve `composition_depth` from the core module at call
    # time. SafeAdaptiveMemoryRunner resolves its reporting copy from the safe module. Patch both
    # only for this explicit launch profile; ordinary Experiment 007 tests/imports remain unchanged.
    core.composition_depth = accelerated_depth
    safe.composition_depth = accelerated_depth
    core.MAX_LEVEL = len(DEPTH_SCHEDULE)
    safe.MAX_LEVEL = len(DEPTH_SCHEDULE)


class AcceleratedSafeRunner(safe.SafeAdaptiveMemoryRunner):
    def __init__(self, *args, **kwargs):
        configure_accelerated_schedule()
        super().__init__(*args, **kwargs)

    def _write_environment(self) -> None:
        super()._write_environment()
        path = self.output_dir / "environment.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["difficulty_profile"] = {
            "name": "accelerated-one-hour-frontier-v1",
            "stage_count": len(DEPTH_SCHEDULE),
            "composition_depths": list(DEPTH_SCHEDULE),
            "adaptive_to_model_results": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_config(path: str) -> ExperimentConfig:
    return ExperimentConfig.from_json(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the accelerated, failure-resilient Experiment 007 external-memory frontier"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    configure_accelerated_schedule()
    config = _load_config(args.config)
    output = Path(args.output_dir) if args.output_dir else Path("results") / config.experiment_id
    client = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    runner = AcceleratedSafeRunner(config, client=client, output_dir=output)
    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0

    if args.preflight_only:
        deterministic = core.deterministic_preflight(config.seed)
        live = runner.live_preflight()
        report = {
            "deterministic": deterministic,
            "live": live,
            "scheduler": "AcceleratedSafeRunner",
            "depth_schedule": list(DEPTH_SCHEDULE),
            "passed": deterministic["passed"] and live["passed"],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2

    summary = runner.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("capability_valid") else 2


if __name__ == "__main__":
    raise SystemExit(main())
