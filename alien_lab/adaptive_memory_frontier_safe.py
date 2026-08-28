from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adaptive_memory_frontier import (
    ARM_FULL,
    ARM_NONE,
    ARM_RETRIEVED,
    FRONTIER_PASS_THRESHOLD,
    MAX_LEVEL,
    AdaptiveMemoryRunner,
    bootstrap_store,
    build_level_packet,
    composition_depth,
    deterministic_preflight,
)
from .experiment import ExperimentConfig
from .ollama import OllamaClient
from .scoring_repair import StrictFinalAnswerClient


PRIMARY_ARM = ARM_RETRIEVED
CONTROL_ARMS = (ARM_NONE, ARM_FULL)


class SafeAdaptiveMemoryRunner(AdaptiveMemoryRunner):
    """Schedule Experiment 007 so secondary controls cannot starve the primary frontier.

    The task generator, memory promotion, scorer, model controls, and prompts are inherited unchanged.
    This class changes only scheduling and interpretation:

    - RETRIEVED always runs first.
    - A possible primary failure is confirmed before spending time on controls.
    - NONE/FULL becoming unusable is recorded as a control boundary, never converted into a
      retrieved-memory capability failure.
    - A confirmation packet starts only when runtime reserve predicts it can finish cleanly.
    """

    def _can_finish_calls(self, count: int) -> bool:
        if count < 1:
            raise ValueError("count must be >= 1")
        # P95 is measured from completed calls. The 1.5 multiplier absorbs level-to-level growth.
        # Keep an absolute 30s/call floor so an unusually fast preflight cannot remove the reserve.
        seconds_per_call = max(30.0, self._p95_duration() * 1.5)
        required = count * seconds_per_call + self.config.safety_margin_seconds
        return self._remaining() > required

    @staticmethod
    def _control_usable(record: dict[str, Any]) -> bool:
        return record.get("status") == "OK"

    def _skipped_control(self, level: int, arm: str, reason: str) -> dict[str, Any]:
        return {
            "level": level,
            "phase": "frontier",
            "arm": arm,
            "model": self.config.model,
            "status": "SKIPPED_TIME_RESERVE",
            "accuracy": None,
            "reason": reason,
        }

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        raw_paths = [
            self.output_dir / "runs.jsonl",
            self.output_dir / "observations.jsonl",
            self.output_dir / "memory.jsonl",
        ]
        if any(path.exists() for path in raw_paths):
            raise RuntimeError(
                f"output directory already contains raw Experiment 007 evidence: {self.output_dir}"
            )

        self._started = self.clock()
        self._deadline = self._started + self.config.ceiling_minutes * 60.0
        self._write_environment()
        environment_path = self.output_dir / "environment.json"
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
        environment["scheduler"] = {
            "name": "SafeAdaptiveMemoryRunner",
            "primary_first": PRIMARY_ARM,
            "controls_after_primary": list(CONTROL_ARMS),
            "confirmation_before_controls_on_primary_miss": True,
        }
        environment_path.write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        deterministic = deterministic_preflight(self.config.seed)
        live = self.live_preflight()
        preflight = {
            "deterministic": deterministic,
            "live": live,
            "passed": deterministic["passed"] and live["passed"],
        }
        (self.output_dir / "preflight.json").write_text(
            json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if not preflight["passed"]:
            self.summary = {
                "interpretation": "PREFLIGHT_FAILED",
                "capability_valid": False,
                "preflight_passed": False,
                "levels_completed": 0,
            }
            (self.output_dir / "summary.json").write_text(
                json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            self._write_report()
            return self.summary

        store = bootstrap_store(self.config.seed)
        self._write_bootstrap_memory(store)

        interpretation = "FRONTIER_NOT_REACHED_MAX_LEVEL"
        capability_valid = True
        last_passing: int | None = None
        confirmed_failure_level: int | None = None
        frontier_rules: int | None = None
        retrieved_context_cap: int | None = None
        no_memory_first_failure: int | None = None
        no_memory_first_unusable: int | None = None
        full_memory_first_failure: int | None = None
        full_memory_first_unusable: int | None = None
        full_memory_context_cap: int | None = None
        unstable_levels: list[int] = []

        for level in range(1, MAX_LEVEL + 1):
            # Three matched arms are expected in the ordinary case. Refuse to begin a level if the
            # measured reserve says they cannot all fit.
            if not self._can_finish_calls(3):
                interpretation = "FRONTIER_NOT_REACHED_TIME_LIMIT"
                break

            tasks, sealed = build_level_packet(self.config.seed, level, store)
            model_seed = self.config.seed + 500_000 + level
            primary = self._run_arm(
                level,
                tasks,
                sealed,
                store,
                PRIMARY_ARM,
                model_seed=model_seed,
                phase="frontier",
            )
            arms: dict[str, dict[str, Any]] = {PRIMARY_ARM: primary}
            confirmation: dict[str, Any] | None = None
            confirmed_failure = False

            if primary["status"] == "CONTEXT_CAP_REACHED":
                retrieved_context_cap = level
                interpretation = "RETRIEVED_MEMORY_CONTEXT_CAP_FOUND"
                level_row = {
                    "level": level,
                    "memory_rule_count": len(store),
                    "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
                    "composition_depth": composition_depth(level),
                    "arms": arms,
                    "confirmation": None,
                    "promoted_macro_count": 0,
                }
                self.levels.append(level_row)
                break

            if primary["status"] != "OK":
                capability_valid = False
                interpretation = "INVALID_PRIMARY_PACKET"
                self.levels.append({
                    "level": level,
                    "memory_rule_count": len(store),
                    "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
                    "composition_depth": composition_depth(level),
                    "arms": arms,
                    "confirmation": None,
                    "promoted_macro_count": 0,
                })
                break

            primary_accuracy = primary["accuracy"]
            if primary_accuracy is None:
                capability_valid = False
                interpretation = "INVALID_PRIMARY_PACKET"
                break

            # Confirmation is more important than controls: it decides whether a miss is a real
            # frontier. Never let FULL/NONE consume that reserve first.
            if primary_accuracy < FRONTIER_PASS_THRESHOLD:
                if not self._can_finish_calls(3):
                    interpretation = "FRONTIER_UNCONFIRMED_TIME_LIMIT"
                    self.levels.append({
                        "level": level,
                        "memory_rule_count": len(store),
                        "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
                        "composition_depth": composition_depth(level),
                        "arms": arms,
                        "confirmation": None,
                        "promoted_macro_count": 0,
                    })
                    break
                confirmation_tasks, confirmation_sealed = build_level_packet(
                    self.config.seed,
                    level,
                    store,
                    variant=1,
                )
                confirmation = self._run_arm(
                    level,
                    confirmation_tasks,
                    confirmation_sealed,
                    store,
                    PRIMARY_ARM,
                    model_seed=self.config.seed + 900_000 + level,
                    phase="confirmation",
                )
                if confirmation["status"] != "OK" or confirmation["accuracy"] is None:
                    capability_valid = False
                    interpretation = "INVALID_CONFIRMATION_PACKET"
                else:
                    confirmed_failure = self.confirmed_failure(
                        primary_accuracy=primary_accuracy,
                        confirmation_accuracy=confirmation["accuracy"],
                    )

            # Controls are useful comparisons, but they are not authority over the primary result.
            # Each starts only if its own reserve remains.
            for arm in CONTROL_ARMS:
                if self._can_finish_calls(1):
                    arms[arm] = self._run_arm(
                        level,
                        tasks,
                        sealed,
                        store,
                        arm,
                        model_seed=model_seed,
                        phase="frontier",
                    )
                else:
                    arms[arm] = self._skipped_control(
                        level,
                        arm,
                        "runtime reserve protected the completed primary measurement",
                    )

            none = arms.get(ARM_NONE)
            if none is not None:
                if none.get("status") == "OK" and none.get("accuracy") is not None:
                    if none["accuracy"] < FRONTIER_PASS_THRESHOLD and no_memory_first_failure is None:
                        no_memory_first_failure = level
                elif no_memory_first_unusable is None:
                    no_memory_first_unusable = level

            full = arms.get(ARM_FULL)
            if full is not None:
                if full.get("status") == "CONTEXT_CAP_REACHED" and full_memory_context_cap is None:
                    full_memory_context_cap = level
                elif full.get("status") == "OK" and full.get("accuracy") is not None:
                    if full["accuracy"] < FRONTIER_PASS_THRESHOLD and full_memory_first_failure is None:
                        full_memory_first_failure = level
                elif full_memory_first_unusable is None:
                    full_memory_first_unusable = level

            level_row: dict[str, Any] = {
                "level": level,
                "memory_rule_count": len(store),
                "memory_snapshot_fingerprint": store.snapshot_fingerprint(),
                "composition_depth": composition_depth(level),
                "arms": arms,
                "confirmation": confirmation,
                "promoted_macro_count": 0,
            }
            self.levels.append(level_row)

            if not capability_valid:
                break

            if confirmed_failure:
                confirmed_failure_level = level
                frontier_rules = len(store)
                interpretation = "RETRIEVED_MEMORY_FRONTIER_FOUND"
                break

            # A primary pass teaches from the primary packet. A one-off primary miss that the fresh
            # confirmation disproves teaches only from the confirmation packet, never from the miss.
            if primary_accuracy >= FRONTIER_PASS_THRESHOLD:
                last_passing = level
                promotion_tasks = tasks
                promotion_run = primary
            else:
                unstable_levels.append(level)
                if confirmation is None or confirmation["accuracy"] < FRONTIER_PASS_THRESHOLD:
                    capability_valid = False
                    interpretation = "INTEGRITY_FAILURE_UNCONFIRMED_PROMOTION"
                    break
                last_passing = level
                promotion_tasks = confirmation_tasks
                promotion_run = confirmation

            promoted = self._promote_from_run(
                store,
                promotion_tasks,
                promotion_run,
                learned_level=level,
            )
            level_row["promoted_macro_count"] = len(promoted)
            if len(promoted) < 7:
                capability_valid = False
                interpretation = "INVALID_MEMORY_PROMOTION"
                break

        self.summary = {
            "interpretation": interpretation,
            "capability_valid": capability_valid,
            "preflight_passed": True,
            "scheduler": "SafeAdaptiveMemoryRunner",
            "model": self.config.model,
            "levels_completed": len(self.levels),
            "retrieved_last_passing_level": last_passing,
            "retrieved_first_confirmed_failure_level": confirmed_failure_level,
            "retrieved_context_cap_level": retrieved_context_cap,
            "memory_rules_at_frontier": frontier_rules,
            "composition_depth_at_frontier": (
                composition_depth(confirmed_failure_level)
                if confirmed_failure_level is not None
                else None
            ),
            "no_memory_first_failure_level": no_memory_first_failure,
            "no_memory_first_unusable_level": no_memory_first_unusable,
            "full_memory_first_failure_level": full_memory_first_failure,
            "full_memory_first_unusable_level": full_memory_first_unusable,
            "full_memory_context_cap_level": full_memory_context_cap,
            "no_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_NONE),
            "full_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_FULL),
            "retrieved_memory_aggregate_accuracy": self._aggregate_accuracy(ARM_RETRIEVED),
            "unstable_levels": unstable_levels,
            "max_rules_learned": len(store),
            "final_memory_snapshot_fingerprint": store.snapshot_fingerprint(),
            "level_results": self.levels,
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._write_report()
        return self.summary


def _load_config(path: str) -> ExperimentConfig:
    return ExperimentConfig.from_json(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Experiment 007 with failure-resilient primary-first scheduling"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    output = Path(args.output_dir) if args.output_dir else Path("results") / config.experiment_id
    client = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    runner = SafeAdaptiveMemoryRunner(config, client=client, output_dir=output)
    runner._started = runner.clock()
    runner._deadline = runner._started + config.ceiling_minutes * 60.0

    if args.preflight_only:
        deterministic = deterministic_preflight(config.seed)
        live = runner.live_preflight()
        report = {
            "deterministic": deterministic,
            "live": live,
            "scheduler": "SafeAdaptiveMemoryRunner",
            "passed": deterministic["passed"] and live["passed"],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2

    summary = runner.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("capability_valid") else 2


if __name__ == "__main__":
    raise SystemExit(main())
