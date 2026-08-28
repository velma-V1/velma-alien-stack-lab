from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from .compiler import compile_workspace
from .design import PRIMITIVES
from .experiment import ExperimentConfig, ExperimentRunner, parse_packet_response
from .ollama import ModelResult, OllamaClient
from .serialize import render_packet
from .taskgen import generate_taskset


class StrictFinalAnswerClient:
    """Force direct final-answer generation and reject unscorable completions.

    Experiments 001-002 proved that think=True plus a short num_predict budget
    can consume the entire generation budget in Ollama's `thinking` field while
    leaving `response` blank. The base evaluator parses only `response`, so
    those runs cannot be classified as wrong answers.

    This wrapper forces think=False for the capability-validation path and
    changes status from OK to UNSCORABLE whenever the final response is blank,
    violates the exact packet-output contract, or hits the generation ceiling.
    """

    def __init__(self, inner: OllamaClient) -> None:
        self.inner = inner

    @property
    def base_url(self) -> str:
        return self.inner.base_url

    def model_metadata(self, model: str, timeout_seconds: float = 5.0) -> dict:
        return self.inner.model_metadata(model, timeout_seconds=timeout_seconds)

    @staticmethod
    def _task_count(prompt: str) -> int:
        count = len(re.findall(r"(?m)^TASK\s+\d+\s*$", prompt))
        return max(1, count)

    @staticmethod
    def _complete_response(response: str | None, task_count: int) -> bool:
        if not response or not response.strip():
            return False
        parts = [rf"{i}\s*:\s*[ABCD]" for i in range(1, task_count + 1)]
        pattern = r"^\s*" + r"\s+".join(parts) + r"\s*$"
        return re.fullmatch(pattern, response, flags=re.IGNORECASE) is not None

    def generate(self, **kwargs) -> ModelResult:
        call = dict(kwargs)
        call["think"] = False
        result = self.inner.generate(**call)
        if result.status != "OK":
            return result

        task_count = self._task_count(str(call.get("prompt", "")))
        complete = self._complete_response(result.response, task_count)
        if result.hit_ceiling or result.done_reason == "length" or not complete:
            return replace(result, status="UNSCORABLE")
        return result


class ScoringRepairRunner(ExperimentRunner):
    """One-cube validation runner with a mandatory live scoring preflight."""

    def _can_start_optional(self) -> bool:
        # Experiment 003 exists only to prove scoring integrity. Do not spend
        # model time on optional scientific phases until the evaluator is valid.
        return False

    def _execute_packet(self, *args, **kwargs) -> bool:
        before = len(self.records)
        completed = super()._execute_packet(*args, **kwargs)
        if len(self.records) > before and self.records[-1].status == "UNSCORABLE":
            return False
        return completed

    def preflight(self) -> dict[str, Any]:
        if self.client is None:
            raise RuntimeError("preflight requires a model client")

        public, _ = generate_taskset(self.config.seed)
        tasks = list(public.discovery)
        full_order = tuple(PRIMITIVES)
        full_set = tuple(PRIMITIVES)
        workspaces = [
            compile_workspace(task.compiler_view(), full_set, order=full_order)
            for task in tasks
        ]

        prompts = [
            ("RAW", render_packet(tasks, mode="raw")),
            ("STRUCTURED", render_packet(tasks, mode="structured")),
            ("FULL", render_packet(tasks, mode="workspace", workspaces=workspaces)),
        ]

        checks: list[dict[str, Any]] = []
        ids = [task.task_id for task in tasks]
        for index, (name, prompt) in enumerate(prompts, 1):
            result = self.client.generate(
                model=self.config.model,
                prompt=prompt,
                num_ctx=self.config.context_limit,
                num_predict=self.config.discovery_budget,
                temperature=self.config.temperature,
                seed=self.config.seed + 9000 + index,
                timeout_seconds=120.0,
            )
            parsed = parse_packet_response(result.response, ids) if result.status == "OK" else {x: None for x in ids}
            parseable = sum(value is not None for value in parsed.values())
            checks.append({
                "condition": name,
                "status": result.status,
                "done_reason": result.done_reason,
                "hit_ceiling": result.hit_ceiling,
                "eval_tokens": result.eval_tokens,
                "response": result.response,
                "thinking_chars": len(result.thinking or ""),
                "parseable_answers": parseable,
                "required_answers": len(ids),
                "passed": (
                    result.status == "OK"
                    and not result.hit_ceiling
                    and parseable == len(ids)
                    and bool((result.response or "").strip())
                ),
            })

        report = {
            "experiment_id": self.config.experiment_id,
            "model": self.config.model,
            "context_limit": self.config.context_limit,
            "thinking_enabled": False,
            "budget": self.config.discovery_budget,
            "checks": checks,
            "passed": all(item["passed"] for item in checks),
        }
        return report

    def run(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        preflight = self.preflight()
        (self.output_dir / "preflight.json").write_text(
            json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if not preflight["passed"]:
            raise RuntimeError(
                "scoring preflight failed; no causal cube was started. "
                "Inspect preflight.json before changing any generation budget."
            )

        records = super().run()
        unscorable = sum(1 for record in records if record.status == "UNSCORABLE")
        discovery_ok = sum(1 for record in records if record.phase == "discovery" and record.status == "OK")
        capability_valid = unscorable == 0 and discovery_ok == 65 and self.summary.get("incomplete_reason") is None
        self.summary["scoring_integrity"] = {
            "preflight_passed": True,
            "thinking_enabled": False,
            "unscorable_generations": unscorable,
            "discovery_ok_generations": discovery_ok,
            "required_discovery_generations": 65,
            "capability_valid": capability_valid,
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(self.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return records


def _load_config(path: str) -> ExperimentConfig:
    return ExperimentConfig.from_json(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate repaired VELMA alien-stack scoring")
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    client = StrictFinalAnswerClient(OllamaClient(config.ollama_url))
    output = Path(args.output_dir) if args.output_dir else Path("results") / config.experiment_id
    runner = ScoringRepairRunner(config, client=client, output_dir=output)

    if args.preflight_only:
        report = runner.preflight()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2

    runner.run()
    print(json.dumps(runner.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
