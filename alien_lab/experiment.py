from __future__ import annotations

import argparse
import csv
import platform
import subprocess
import sys
from datetime import datetime, timezone
import json
import math
import re
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from . import LAB_VERSION, RUN_SCHEMA_VERSION
from .compiler import compile_workspace, fuse_workspace, recursive_fuse_workspace
from .design import PRIMITIVES, all_subsets, subset_id
from .experiment_analysis import ExperimentAnalysisMixin
from .experiment_optional import ExperimentOptionalMixin
from .ollama import OllamaClient
from .records import RunRecord, append_jsonl, stable_hash
from .serialize import render_packet
from .taskgen import generate_taskset, write_sealed_taskset
from .types import Task


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "001-combinatorial-alien-stack"
    model: str = "qwen3.5:9b-q8_0"
    quantization: str = "Q8_0"
    context_limit: int = 25600
    temperature: float = 0.0
    seed: int = 20260828
    target_minutes: float = 55.0
    ceiling_minutes: float = 60.0
    safety_margin_seconds: float = 15.0
    discovery_budget: int = 128
    transfer_budget: int = 192
    small_budget: int = 96
    medium_budget: int = 192
    large_budget: int = 400
    ollama_url: str = "http://localhost:11434"

    @classmethod
    def from_json(cls, path: Path) -> "ExperimentConfig":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


def parse_packet_response(response: str | None, task_ids: list[str]) -> dict[str, str | None]:
    if not response:
        return {task_id: None for task_id in task_ids}
    matches = re.findall(r"(?i)(?:task\s*)?(\d+)\s*[:=\-]\s*([ABCD])\b", response)
    by_pos = {int(pos): letter.upper() for pos, letter in matches}
    if not by_pos:
        letters = re.findall(r"(?i)\b([ABCD])\b", response)
        by_pos = {i + 1: letter.upper() for i, letter in enumerate(letters[: len(task_ids)])}
    return {task_id: by_pos.get(i + 1) for i, task_id in enumerate(task_ids)}


class ExperimentRunner(ExperimentAnalysisMixin, ExperimentOptionalMixin):
    def __init__(
        self,
        config: ExperimentConfig,
        *,
        client: OllamaClient | None,
        clock=time.monotonic,
        output_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.clock = clock
        self.output_dir = output_dir or Path("results") / config.experiment_id
        self.records: list[RunRecord] = []
        self.observations: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}
        self._sealed: dict[str, dict[str, Any]] = {}
        self._started = 0.0
        self._deadline = 0.0
        self._run_seq = 0


    def _write_environment_snapshot(self) -> None:
        model_metadata = None
        if self.client is not None and hasattr(self.client, "model_metadata"):
            model_metadata = self.client.model_metadata(self.config.model, timeout_seconds=5.0)
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=Path.cwd(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
            git_commit = proc.stdout.strip() if proc.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            git_commit = None
        snapshot = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "lab_version": LAB_VERSION,
            "run_schema_version": RUN_SCHEMA_VERSION,
            "git_commit": git_commit,
            "python_version": sys.version,
            "platform": platform.platform(),
            "config": asdict(self.config),
            "model_metadata": model_metadata,
        }
        (self.output_dir / "environment.json").write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def dry_run(self) -> dict[str, Any]:
        public, _ = generate_taskset(self.config.seed)
        return {
            "model": self.config.model,
            "context_limit": self.config.context_limit,
            "target_minutes": self.config.target_minutes,
            "ceiling_minutes": self.config.ceiling_minutes,
            "discovery_raw_calls": 1,
            "discovery_structured_calls": len(all_subsets()),
            "discovery_tasks_per_call": len(public.discovery),
            "boolean_cube_task_observations": len(all_subsets()) * len(public.discovery),
            "raw_task_observations": len(public.discovery),
            "primitive_count": len(PRIMITIVES),
            "primitives": list(PRIMITIVES),
            "optional_phase_catalog": [
                "transfer",
                "compute_substitution",
                "order_effect",
                "higher_order_order",
                "fusion_probe",
                "recursive_fusion",
                "batching_control",
                "antagonism_control",
                "presentation_perturbation",
                "budget_curve",
                "robustness_replication",
            ],
        }

    def run(self) -> list[RunRecord]:
        if self.client is None:
            raise RuntimeError("run() requires a model client; use dry_run() without one")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if (self.output_dir / "runs.jsonl").exists() or (self.output_dir / "observations.jsonl").exists():
            raise RuntimeError(
                f"output directory already contains raw run evidence: {self.output_dir}. "
                "Use a new output directory; historical evidence is append-only and cannot be mixed with a new run."
            )
        self._write_environment_snapshot()
        public, sealed = generate_taskset(self.config.seed)
        self._sealed = sealed.answers
        write_sealed_taskset(
            public,
            sealed,
            self.output_dir / "tasks.public.json",
            self.output_dir / "sealed" / "answers.json",
        )
        self._started = self.clock()
        self._deadline = self._started + self.config.ceiling_minutes * 60.0

        # RAW control first, then the complete 64-arm Boolean cube. These are
        # required and never displaced by optional follow-up work.
        if not self._execute_packet(
            list(public.discovery), phase="discovery", representation="RAW",
            subset=frozenset(), order=(), budget=self.config.discovery_budget,
            tag="raw-control", taskset_seed=self.config.seed,
        ):
            return self._finish()

        for subset in all_subsets():
            if self._remaining() <= 0:
                break
            rep = "STRUCTURED" if not subset else "COMPOUND"
            order = tuple(p for p in PRIMITIVES if p in subset)
            completed = self._execute_packet(
                list(public.discovery), phase="discovery", representation=rep,
                subset=subset, order=order, budget=self.config.discovery_budget,
                tag=subset_id(subset), taskset_seed=self.config.seed,
            )
            if not completed:
                break

        if len([r for r in self.records if r.phase == "discovery" and r.status == "OK"]) < 65:
            return self._finish(incomplete_reason="discovery_cube_incomplete")

        analysis = self._analyze_discovery()
        optional_jobs = self._build_optional_jobs(public, analysis)
        for job in optional_jobs:
            if not self._can_start_optional():
                break
            if job["kind"] == "packet":
                completed = self._execute_packet(**job["kwargs"])
            else:
                completed = self._execute_packet(**job["kwargs"])
            if not completed:
                break

        return self._finish(discovery_analysis=analysis)

    def _remaining(self) -> float:
        return max(0.0, self._deadline - self.clock())

    def _duration_estimate(self) -> float:
        durations = sorted(r.wall_ms / 1000.0 for r in self.records if r.status == "OK" and r.wall_ms > 0)
        if not durations:
            return 10.0
        index = max(0, math.ceil(0.95 * len(durations)) - 1)
        return durations[index]

    def _can_start_optional(self) -> bool:
        required = self._duration_estimate() + self.config.safety_margin_seconds
        return self._remaining() > required

    def _next_run_id(self, phase: str) -> str:
        self._run_seq += 1
        return f"{self.config.experiment_id}:{phase}:{self._run_seq:04d}"

    def _execute_packet(
        self,
        tasks: list[Task],
        *,
        phase: str,
        representation: str,
        subset: frozenset[str],
        order: tuple[str, ...],
        budget: int,
        tag: str,
        taskset_seed: int,
        evaluator_override: dict[str, dict[str, Any]] | None = None,
        fusion_depth: int = 0,
    ) -> bool:
        remaining = self._remaining()
        if remaining <= 0:
            return False

        compiler_started = time.perf_counter()
        workspaces = []
        if representation == "RAW":
            prompt = render_packet(tasks, mode="raw")
        elif not subset:
            prompt = render_packet(tasks, mode="structured")
        else:
            workspaces = [compile_workspace(t.compiler_view(), tuple(subset), order=order) for t in tasks]
            if fusion_depth == 1:
                for task, ws in zip(tasks, workspaces):
                    fuse_workspace(task.compiler_view(), ws)
            elif fusion_depth > 1:
                for task, ws in zip(tasks, workspaces):
                    recursive_fuse_workspace(task.compiler_view(), ws, depth=fusion_depth)
            prompt = render_packet(tasks, mode="workspace", workspaces=workspaces)
        compiler_ms = (time.perf_counter() - compiler_started) * 1000.0

        source_payload = [asdict(t.compiler_view()) for t in tasks]
        workspace_payload = [ws.to_dict() for ws in workspaces]
        source_hash = stable_hash(source_payload)
        workspace_hash = stable_hash(workspace_payload) if workspaces else stable_hash({"representation": representation})
        prompt_hash = stable_hash({"prompt": prompt})
        prompt_bytes = len(prompt.encode("utf-8"))
        source_bytes = len(json.dumps(source_payload, sort_keys=True).encode("utf-8"))
        workspace_bytes = len(json.dumps(workspace_payload, sort_keys=True).encode("utf-8")) if workspaces else 0
        workspace_by_task = {task.task_id: ws for task, ws in zip(tasks, workspaces)}

        run_id = self._next_run_id(phase)
        result = self.client.generate(
            model=self.config.model,
            prompt=prompt,
            num_ctx=self.config.context_limit,
            num_predict=budget,
            temperature=self.config.temperature,
            seed=self.config.seed + self._run_seq,
            timeout_seconds=max(0.001, remaining),
        )
        task_ids = [t.task_id for t in tasks]
        predictions = parse_packet_response(result.response, task_ids) if result.status == "OK" else {tid: None for tid in task_ids}

        derived = []
        discarded = []
        contradictions = []
        for task, ws in zip(tasks, workspaces):
            derived.extend({"task_id": task.task_id, "derivation": asdict(d)} for d in ws.derivations)
            discarded.extend(f"{task.task_id}:{item}" for item in ws.discarded_evidence)
            contradictions.extend({"task_id": task.task_id, **item} for item in ws.contradictions)

        evaluator_map = evaluator_override or self._sealed
        per_task = []
        for task in tasks:
            evaluator = evaluator_map[task.task_id]
            prediction = predictions[task.task_id]
            success = None if result.status != "OK" else prediction == evaluator["answer"]
            task_ws = workspace_by_task.get(task.task_id)
            observation = {
                "run_id": run_id,
                "task_id": task.task_id,
                "task_family": task.family,
                "taskset_seed": taskset_seed,
                "phase": phase,
                "representation": representation,
                "subset_id": subset_id(subset),
                "primitives": [p for p in PRIMITIVES if p in subset],
                "pass_order": list(task_ws.pass_order) if task_ws else list(order),
                "reasoning_budget": budget,
                "prediction": prediction,
                "expected": evaluator["answer"],
                "verified_success": success,
                "deterministic_unique": evaluator.get("deterministic_unique", False),
                "source_hash": source_hash,
                "workspace_hash": workspace_hash,
                "generation_eval_tokens": result.eval_tokens,
                "amortized_eval_tokens": (result.eval_tokens / len(tasks)) if tasks else 0,
                "generation_wall_ms": result.wall_ms,
                "amortized_wall_ms": (result.wall_ms / len(tasks)) if tasks else 0,
                "ollama_total_ns": result.total_ns,
                "ollama_load_ns": result.load_ns,
                "hit_ceiling": result.hit_ceiling,
                "compiler_ms": compiler_ms,
                "pass_timings_ms": dict(task_ws.pass_timings_ms) if task_ws else {},
                "derived_fact_count": len(task_ws.derivations) if task_ws else 0,
                "discarded_count": len(task_ws.discarded_evidence) if task_ws else 0,
                "contradiction_count": len(task_ws.contradictions) if task_ws else 0,
                "fusion_depth": fusion_depth,
                "batch_size": len(tasks),
                "prompt_hash": prompt_hash,
                "prompt_bytes": prompt_bytes,
                "source_bytes": source_bytes,
                "workspace_bytes": workspace_bytes,
                "status": result.status,
            }
            self.observations.append(observation)
            append_jsonl(self.output_dir / "observations.jsonl", observation)
            per_task.append({
                "task_id": task.task_id,
                "prediction": prediction,
                "expected": evaluator["answer"],
                "verified_success": success,
            })

        scored = [x["verified_success"] for x in per_task if x["verified_success"] is not None]
        record = RunRecord(
            run_id=run_id,
            task_id="packet:" + ",".join(task_ids),
            status=result.status,
            experiment_id=self.config.experiment_id,
            phase=phase,
            family="packet" if len(tasks) > 1 else tasks[0].family,
            model=self.config.model,
            quantization=self.config.quantization,
            context_limit=self.config.context_limit,
            reasoning_budget=budget,
            temperature=self.config.temperature,
            seed=self.config.seed + self._run_seq,
            representation=representation,
            primitives=[p for p in PRIMITIVES if p in subset],
            pass_order=(list(workspaces[0].pass_order) if workspaces else list(order)),
            source_hash=source_hash,
            workspace_hash=workspace_hash,
            derived_facts=derived,
            discarded_evidence=discarded,
            contradictions=contradictions,
            compiler_ms=compiler_ms,
            prompt_tokens=result.prompt_tokens,
            eval_tokens=result.eval_tokens,
            prompt_eval_ns=result.prompt_eval_ns,
            eval_ns=result.eval_ns,
            total_ns=result.total_ns,
            load_ns=result.load_ns,
            wall_ms=result.wall_ms,
            tokens_per_second=result.tokens_per_second,
            done_reason=result.done_reason,
            hit_ceiling=result.hit_ceiling,
            thinking=result.thinking,
            response=result.response,
            prediction=" ".join(str(predictions[t]) for t in task_ids) if result.status == "OK" else None,
            expected=" ".join(str(evaluator_map[t]["answer"]) for t in task_ids) if result.status == "OK" else None,
            verified_success=(all(scored) if scored else None),
            deterministic_unique=all(bool(evaluator_map[t].get("deterministic_unique", False)) for t in task_ids),
            metadata={
                "tag": tag,
                "taskset_seed": taskset_seed,
                "task_results": per_task,
                "batch_size": len(tasks),
                "fusion_depth": fusion_depth,
                "prompt_hash": prompt_hash,
                "prompt_text": prompt,
                "prompt_bytes": prompt_bytes,
                "source_bytes": source_bytes,
                "workspace_bytes": workspace_bytes,
                "pass_timings_by_task": {task.task_id: dict(ws.pass_timings_ms) for task, ws in zip(tasks, workspaces)},
                "workspaces_by_task": {task.task_id: ws.to_dict() for task, ws in zip(tasks, workspaces)},
                "packet_accuracy": (sum(bool(x) for x in scored) / len(scored)) if scored else None,
            },
        )
        self.records.append(record)
        append_jsonl(self.output_dir / "runs.jsonl", record)
        return result.status != "TIME_BUDGET_ABORT"







def _load_config(path: str | None) -> ExperimentConfig:
    return ExperimentConfig.from_json(Path(path)) if path else ExperimentConfig()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VELMA alien-stack combinatorial experiment")
    parser.add_argument("--config")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    cfg = _load_config(args.config)
    output = Path(args.output_dir) if args.output_dir else None
    client = None if args.dry_run else OllamaClient(cfg.ollama_url)
    runner = ExperimentRunner(cfg, client=client, output_dir=output)
    if args.dry_run:
        print(json.dumps(runner.dry_run(), indent=2, sort_keys=True))
        return 0
    runner.run()
    print(json.dumps(runner.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
