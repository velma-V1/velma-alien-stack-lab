from __future__ import annotations

import argparse
import json
import re
import socket
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .final_memory_frontier import (
    ARM_FULL,
    ARM_NONE,
    ARM_RETRIEVED,
    ARMS,
    TITAN_ARMS,
    VARIANTS_PER_LEVEL,
    Final007Runner,
    MemoryStore,
    ModelSpec,
    SuiteConfig,
    _jsonl,
    build_level,
    context_guard,
    generate_bootstrap,
    parse_answers,
    promote_verified,
    render_packet,
    stable_hash,
)
from .ollama import ModelResult


class CapabilityAwareOllamaClient:
    """Ollama client that omits unsupported thinking fields.

    Experiment 007 runs with hidden model thinking disabled when the installed
    model advertises the thinking capability. Models that do not advertise it
    receive no top-level `think` field at all. This avoids conflating hidden
    reasoning budget with external-memory effects and avoids Ollama 400s on
    non-thinking models.
    """

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def _tags(self, timeout_seconds: float = 5.0) -> dict[str, Any]:
        request = urllib.request.Request(self.base_url + "/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=max(0.001, timeout_seconds)) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def model_metadata(self, model: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
        doc = self._tags(timeout_seconds)
        for item in doc.get("models", []):
            if item.get("name") == model or item.get("model") == model:
                return item
        raise RuntimeError(f"MODEL_UNAVAILABLE: exact Ollama tag not installed: {model}")

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        num_ctx: int,
        num_predict: int,
        temperature: float,
        seed: int,
        timeout_seconds: float,
        keep_alive: str = "70m",
        think: bool | None = None,
    ) -> ModelResult:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "temperature": temperature,
                "seed": seed,
            },
        }
        if think is not None:
            payload["think"] = think

        request = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=max(0.001, timeout_seconds)) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
        except (TimeoutError, socket.timeout):
            return ModelResult(
                status="TIME_BUDGET_ABORT",
                wall_ms=(time.perf_counter() - started) * 1000,
                done_reason="time_budget_abort",
            )
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                return ModelResult(
                    status="TIME_BUDGET_ABORT",
                    wall_ms=(time.perf_counter() - started) * 1000,
                    done_reason="time_budget_abort",
                )
            raise

        eval_count = int(doc.get("eval_count") or 0)
        done_reason = str(doc.get("done_reason") or "")
        return ModelResult(
            status="OK",
            response=doc.get("response"),
            thinking=doc.get("thinking"),
            done_reason=done_reason,
            prompt_tokens=int(doc.get("prompt_eval_count") or 0),
            eval_tokens=eval_count,
            prompt_eval_ns=int(doc.get("prompt_eval_duration") or 0),
            eval_ns=int(doc.get("eval_duration") or 0),
            total_ns=int(doc.get("total_duration") or 0),
            load_ns=int(doc.get("load_duration") or 0),
            wall_ms=(time.perf_counter() - started) * 1000,
            hit_ceiling=(done_reason == "length" or eval_count >= num_predict),
        )


class Repaired007Runner(Final007Runner):
    """Real-Ollama repair layer for the final Experiment 007 harness."""

    def __init__(self, config: SuiteConfig, client_factory: Callable[[str], Any], output_dir: Path):
        super().__init__(config, client_factory, output_dir)
        self._metadata_cache: dict[str, dict[str, Any]] = {}

    def _metadata(self, client: Any, spec: ModelSpec) -> dict[str, Any]:
        if spec.model not in self._metadata_cache:
            self._metadata_cache[spec.model] = client.model_metadata(spec.model)
        return self._metadata_cache[spec.model]

    def _thinking_arg(self, client: Any, spec: ModelSpec) -> bool | None:
        caps = set(self._metadata(client, spec).get("capabilities", []))
        return False if "thinking" in caps else None

    @staticmethod
    def _terminal_failure_status(failures: list[dict[str, Any]]) -> str:
        if failures and all(row.get("status") == "OUTPUT_CAP_REACHED" for row in failures):
            return "OUTPUT_CAP_REACHED"
        if failures and all(row.get("status") == "TIME_BUDGET_ABORT" for row in failures):
            return "TIME_BUDGET_ABORT"
        return "INFRASTRUCTURE_UNSCORABLE"

    def _safe_generate(self, client: Any, spec: ModelSpec, prompt: str, seed: int) -> tuple[Any | None, list[dict[str, Any]]]:
        failures: list[dict[str, Any]] = []
        think = self._thinking_arg(client, spec)
        caps = list(self._metadata(client, spec).get("capabilities", []))
        for attempt in range(1, self.config.retry_count + 1):
            try:
                result = client.generate(
                    model=spec.model,
                    prompt=prompt,
                    num_ctx=spec.context_limit,
                    num_predict=spec.output_budget,
                    temperature=spec.temperature,
                    seed=seed,
                    timeout_seconds=self.config.call_timeout_seconds,
                    think=think,
                )
                if result.status == "OK" and not getattr(result, "hit_ceiling", False):
                    return result, failures
                terminal = "OUTPUT_CAP_REACHED" if getattr(result, "hit_ceiling", False) else result.status
                failures.append({
                    "attempt": attempt,
                    "status": terminal,
                    "done_reason": getattr(result, "done_reason", ""),
                    "think": think,
                    "capabilities": caps,
                })
            except Exception as exc:
                failures.append({
                    "attempt": attempt,
                    "status": "EXCEPTION",
                    "error": repr(exc),
                    "think": think,
                    "capabilities": caps,
                })
            if attempt < self.config.retry_count:
                time.sleep(0.01)
        return None, failures

    @staticmethod
    def _strict_recovered_choices(text: str | None, expected_count: int) -> list[str] | None:
        if not text:
            return None
        if expected_count == 1:
            match = re.fullmatch(r"\s*([ABCD])\s*", text, flags=re.I)
            return [match.group(1).upper()] if match else None
        pieces = [rf"{i}\s*:\s*([ABCD])" for i in range(1, expected_count + 1)]
        match = re.fullmatch(r"\s*" + r"\s+".join(pieces) + r"\s*", text, flags=re.I)
        return [group.upper() for group in match.groups()] if match else None

    def _format_only_recovery(
        self,
        client: Any,
        spec: ModelSpec,
        raw_response: str,
        expected_count: int,
        seed: int,
    ) -> tuple[list[str] | None, dict[str, Any]]:
        contract = "<LETTER>" if expected_count == 1 else " ".join(
            f"{i}:<LETTER>" for i in range(1, expected_count + 1)
        )
        prompt = "\n".join([
            "FORMAT-ONLY RECOVERY",
            "You are a transcription formatter, not a problem solver.",
            "You are intentionally NOT given the task, rules, choices, or correct answers.",
            "Do not solve, reason, infer, add, remove, reorder, or change any answer choice.",
            f"The source must unambiguously encode exactly {expected_count} A/B/C/D choice(s).",
            f"If it does, return exactly: {contract}",
            "If it does not, return exactly: INVALID",
            "SOURCE RESPONSE:",
            raw_response,
        ])
        think = self._thinking_arg(client, spec)
        meta: dict[str, Any] = {
            "used": True,
            "source_hash": stable_hash(raw_response),
            "status": "FORMAT_RECOVERY_FAILED",
            "response": None,
            "think": think,
        }
        try:
            result = client.generate(
                model=spec.model,
                prompt=prompt,
                num_ctx=spec.context_limit,
                num_predict=min(spec.output_budget, 128),
                temperature=0.0,
                seed=seed,
                timeout_seconds=self.config.call_timeout_seconds,
                think=think,
            )
        except Exception as exc:
            meta["error"] = repr(exc)
            return None, meta
        meta.update({
            "response": getattr(result, "response", None),
            "model_status": getattr(result, "status", ""),
            "done_reason": getattr(result, "done_reason", ""),
            "hit_ceiling": bool(getattr(result, "hit_ceiling", False)),
            "prompt_tokens": int(getattr(result, "prompt_tokens", 0)),
            "eval_tokens": int(getattr(result, "eval_tokens", 0)),
            "wall_ms": float(getattr(result, "wall_ms", 0.0)),
        })
        if getattr(result, "status", "") != "OK" or getattr(result, "hit_ceiling", False):
            return None, meta
        recovered = self._strict_recovered_choices(getattr(result, "response", None), expected_count)
        if recovered is None:
            meta["status"] = "FORMAT_RECOVERY_INVALID"
            return None, meta
        meta["status"] = "OK"
        return recovered, meta

    def _parse_or_recover_answers(
        self,
        client: Any,
        spec: ModelSpec,
        raw_response: str | None,
        task_ids: list[str],
        seed: int,
    ) -> tuple[dict[str, str | None], dict[str, Any]]:
        parsed = parse_answers(raw_response, task_ids)
        if all(parsed[task_id] is not None for task_id in task_ids):
            return parsed, {"used": False, "status": "NOT_NEEDED"}
        recovered, meta = self._format_only_recovery(client, spec, raw_response or "", len(task_ids), seed)
        if recovered is None:
            return parsed, meta
        return {task_id: recovered[i] for i, task_id in enumerate(task_ids)}, meta

    def _preflight_model(self, spec: ModelSpec) -> dict[str, Any]:
        client = self.client_factory(self.config.ollama_url)
        try:
            metadata = self._metadata(client, spec)
        except Exception as exc:
            return {
                "passed": False,
                "status": "MODEL_UNAVAILABLE",
                "model": spec.model,
                "error": repr(exc),
            }

        store = generate_bootstrap(self.config.seed)
        tasks, _ = build_level(self.config.seed, 1, 0, store)
        promote_verified(
            store,
            tasks,
            [{"task_id": task.task_id, "verified_success": True} for task in tasks],
            1,
        )
        ids = [task.task_id for task in tasks]
        arms: dict[str, Any] = {}
        for arm in ARMS:
            prompt, supplied, _, _ = render_packet(tasks, store, arm)
            result, failures = self._safe_generate(client, spec, prompt, self.config.seed ^ 0x700700)
            if result is None:
                arms[arm] = {
                    "status": self._terminal_failure_status(failures),
                    "retry_failures": failures,
                    "memory_supplied_count": len(supplied),
                }
                continue
            parsed, recovery = self._parse_or_recover_answers(
                client, spec, result.response, ids, self.config.seed ^ 0x700701
            )
            format_ok = all(parsed[task_id] is not None for task_id in ids)
            arms[arm] = {
                "status": "OK" if format_ok else "FORMAT_UNSCORABLE",
                "memory_supplied_count": len(supplied),
                "prompt_tokens": getattr(result, "prompt_tokens", 0),
                "eval_tokens": getattr(result, "eval_tokens", 0),
                "done_reason": getattr(result, "done_reason", ""),
                "response": result.response,
                "retry_failures": failures,
                "format_recovery_used": bool(recovery.get("used")),
                "format_recovery_status": recovery.get("status"),
                "format_recovery_response": recovery.get("response"),
                "format_recovery_source_hash": recovery.get("source_hash"),
            }
        passed = all(arms[arm]["status"] == "OK" for arm in ARMS)
        return {
            "passed": passed,
            "status": "OK" if passed else "LIVE_SCORING_PREFLIGHT_FAILED",
            "model": spec.model,
            "metadata": metadata,
            "thinking_arg": self._thinking_arg(client, spec),
            "arms": arms,
        }

    def _run_arm(self, client: Any, spec: ModelSpec, model_dir: Path, level: int, variant: int,
                 tasks: tuple[Any, ...], sealed: dict[str, str], store: MemoryStore, arm: str) -> dict[str, Any]:
        prompt, supplied, raw_steps, compiled_steps = render_packet(tasks, store, arm)
        fits, pbytes, est = context_guard(prompt, spec.context_limit)
        base = {
            "level": level, "variant": variant, "arm": arm, "prompt_hash": stable_hash(prompt),
            "prompt_bytes": pbytes, "estimated_prompt_tokens": est, "memory_supplied": list(supplied),
            "memory_supplied_count": len(supplied), "memory_store_count": len(store.macros),
            "memory_fingerprint": store.fingerprint(), "raw_program_steps": raw_steps,
            "compiled_program_steps": compiled_steps, "steps_saved": raw_steps - compiled_steps,
        }
        if not fits:
            row = {**base, "status": "CONTEXT_CAP_REACHED", "accuracy": None, "task_results": []}
            _jsonl(model_dir / "runs.jsonl", row)
            return row
        result, retry_failures = self._safe_generate(
            client, spec, prompt, self.config.seed + level * 1000 + variant * 10
        )
        if result is None:
            row = {
                **base,
                "status": self._terminal_failure_status(retry_failures),
                "accuracy": None,
                "retry_failures": retry_failures,
                "task_results": [],
            }
            _jsonl(model_dir / "runs.jsonl", row)
            return row
        ids = [task.task_id for task in tasks]
        pred, recovery = self._parse_or_recover_answers(
            client,
            spec,
            result.response,
            ids,
            self.config.seed + level * 1000 + variant * 10 + 1,
        )
        complete = all(pred[task_id] is not None for task_id in ids)
        recovery_fields = {
            "format_recovery_used": bool(recovery.get("used")),
            "format_recovery_status": recovery.get("status"),
            "format_recovery_response": recovery.get("response"),
            "format_recovery_source_hash": recovery.get("source_hash"),
        }
        if not complete:
            row = {
                **base,
                "status": "FORMAT_UNSCORABLE",
                "accuracy": None,
                "response": result.response,
                "retry_failures": retry_failures,
                "task_results": [],
                **recovery_fields,
            }
            _jsonl(model_dir / "runs.jsonl", row)
            return row
        task_results = []
        for task in tasks:
            success = pred[task.task_id] == sealed[task.task_id]
            tr = {
                "task_id": task.task_id,
                "prediction": pred[task.task_id],
                "expected": sealed[task.task_id],
                "verified_success": success,
                "start": task.start,
                "rule_ids": list(task.rule_ids),
            }
            task_results.append(tr)
            _jsonl(model_dir / "observations.jsonl", {**base, **tr})
        accuracy = sum(row["verified_success"] for row in task_results) / len(task_results)
        row = {
            **base,
            "status": "OK",
            "accuracy": accuracy,
            "response": result.response,
            "prompt_tokens": getattr(result, "prompt_tokens", 0),
            "eval_tokens": getattr(result, "eval_tokens", 0),
            "wall_ms": getattr(result, "wall_ms", 0.0),
            "retry_failures": retry_failures,
            "task_results": task_results,
            **recovery_fields,
        }
        _jsonl(model_dir / "runs.jsonl", row)
        return row

    def _run_titan(self, client: Any, spec: ModelSpec, model_dir: Path, store: MemoryStore) -> dict[str, Any]:
        answer, oracle = self._build_titan(self.config.seed, store)
        out = {
            "oracle_hash": stable_hash(oracle),
            "program_steps": len(oracle["ops"]),
            "branch_points": 4,
            "cross_register_joins": 8,
            "nested_joins": 3,
            "raw_rule_applications": oracle["raw_rule_applications"],
            "macro_slots": oracle["macro_slots"],
            "attempts": {},
        }
        for arm in TITAN_ARMS:
            prompt, supplied, rendered_steps = self._titan_prompt(oracle, store, arm)
            fits, pbytes, est = context_guard(prompt, spec.context_limit)
            if not fits:
                rec = {
                    "status": "CONTEXT_CAP_REACHED", "correct": None,
                    "memory_count": len(supplied), "prompt_bytes": pbytes,
                    "estimated_prompt_tokens": est, "rendered_program_steps": rendered_steps,
                }
            else:
                result, failures = self._safe_generate(client, spec, prompt, self.config.seed + 777777)
                if result is None:
                    rec = {
                        "status": self._terminal_failure_status(failures),
                        "correct": None,
                        "memory_count": len(supplied),
                        "retry_failures": failures,
                        "rendered_program_steps": rendered_steps,
                    }
                else:
                    match = re.fullmatch(r"\s*([ABCD])\s*", result.response or "", flags=re.I)
                    recovery = {"used": False, "status": "NOT_NEEDED"}
                    prediction = match.group(1).upper() if match else None
                    if prediction is None:
                        recovered, recovery = self._format_only_recovery(
                            client, spec, result.response or "", 1, self.config.seed + 777778
                        )
                        prediction = recovered[0] if recovered else None
                    rec = {
                        "status": "OK" if prediction else "FORMAT_UNSCORABLE",
                        "correct": bool(prediction == answer) if prediction else None,
                        "prediction": prediction,
                        "expected": answer,
                        "memory_count": len(supplied),
                        "prompt_tokens": getattr(result, "prompt_tokens", 0),
                        "eval_tokens": getattr(result, "eval_tokens", 0),
                        "wall_ms": getattr(result, "wall_ms", 0.0),
                        "rendered_program_steps": rendered_steps,
                        "format_recovery_used": bool(recovery.get("used")),
                        "format_recovery_status": recovery.get("status"),
                        "format_recovery_response": recovery.get("response"),
                        "format_recovery_source_hash": recovery.get("source_hash"),
                    }
            out["attempts"][arm] = rec
            _jsonl(model_dir / "titan.jsonl", {"arm": arm, **rec, "oracle_hash": out["oracle_hash"]})
        return out

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    def run_model(self, spec: ModelSpec) -> dict[str, Any]:
        model_dir = self._model_dir(spec)
        model_dir.mkdir(parents=True, exist_ok=True)
        preflight = self._preflight_model(spec)
        self._write_json_atomic(model_dir / "live_preflight.json", preflight)
        if not preflight["passed"]:
            summary = {
                "model": asdict(spec),
                "execution_completed": False,
                "experiment_valid": False,
                "completed": False,
                "evidence_status": preflight["status"],
                "paired_packet_count": 0,
                "paired_packet_expected": self.config.max_level * VARIANTS_PER_LEVEL,
                "paired_coverage": 0.0,
                "final_memory_count": 0,
                "preflight": preflight,
            }
            self._write_json_atomic(model_dir / "summary.json", summary)
            self._checkpoint(model_dir, {
                "phase": "preflight_failed",
                "completed": False,
                "experiment_valid": False,
                "evidence_status": preflight["status"],
                "summary_hash": stable_hash(summary),
            })
            return summary

        summary = super().run_model(spec)
        paired = int(summary.get("paired_packet_count") or 0)
        expected = self.config.max_level * VARIANTS_PER_LEVEL
        valid = paired > 0
        summary.update({
            "execution_completed": True,
            "experiment_valid": valid,
            "completed": valid,
            "evidence_status": "VALID_EVIDENCE" if valid else "NO_SCORABLE_PAIRED_PACKETS",
            "paired_packet_expected": expected,
            "paired_coverage": paired / expected if expected else 0.0,
            "preflight": preflight,
        })
        self._write_json_atomic(model_dir / "summary.json", summary)
        self._checkpoint(model_dir, {
            "phase": "complete" if valid else "invalid_complete",
            "execution_completed": True,
            "completed": valid,
            "experiment_valid": valid,
            "evidence_status": summary["evidence_status"],
            "memory_count": summary.get("final_memory_count", 0),
            "summary_hash": stable_hash(summary),
        })
        return summary

    def run_suite(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        suite: list[dict[str, Any]] = []
        for spec in self.config.models:
            if not spec.enabled:
                continue
            try:
                suite.append(self.run_model(spec))
            except Exception as exc:
                failure = {
                    "model": asdict(spec),
                    "execution_completed": False,
                    "completed": False,
                    "experiment_valid": False,
                    "evidence_status": "MODEL_RUN_EXCEPTION",
                    "suite_error": repr(exc),
                }
                suite.append(failure)
        suite_execution_completed = all(bool(row.get("execution_completed")) for row in suite)
        suite_valid = bool(suite) and all(bool(row.get("experiment_valid")) for row in suite)
        result = {
            "experiment_id": self.config.experiment_id,
            "models": suite,
            "suite_execution_completed": suite_execution_completed,
            "suite_valid": suite_valid,
            "suite_completed": suite_valid,
            "valid_model_count": sum(bool(row.get("experiment_valid")) for row in suite),
            "model_count": len(suite),
        }
        self._write_json_atomic(self.output_dir / "suite_summary.json", result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", default="results/007-real-ollama-repair")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)

    config = SuiteConfig.from_json(Path(args.config))
    runner = Repaired007Runner(config, CapabilityAwareOllamaClient, Path(args.output_dir))
    if args.preflight_only:
        report = {spec.label: runner._preflight_model(spec) for spec in config.models if spec.enabled}
        print(json.dumps(report, indent=2))
        return 0 if report and all(row["passed"] for row in report.values()) else 2

    result = runner.run_suite()
    print(json.dumps(result, indent=2))
    return 0 if result["suite_valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
