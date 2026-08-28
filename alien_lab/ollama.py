from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class ModelResult:
    status: str
    response: str | None = None
    thinking: str | None = None
    done_reason: str = ""
    prompt_tokens: int = 0
    eval_tokens: int = 0
    prompt_eval_ns: int = 0
    eval_ns: int = 0
    total_ns: int = 0
    load_ns: int = 0
    wall_ms: float = 0.0
    hit_ceiling: bool = False

    @property
    def tokens_per_second(self) -> float:
        seconds = self.eval_ns / 1_000_000_000
        return self.eval_tokens / seconds if seconds > 0 else 0.0


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")


    def model_metadata(self, model: str, timeout_seconds: float = 5.0) -> dict:
        request = urllib.request.Request(self.base_url + "/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=max(0.001, timeout_seconds)) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        for item in doc.get("models", []):
            if item.get("name") == model or item.get("model") == model:
                return item
        raise RuntimeError(f"Ollama model not found: {model}")

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
        think: bool = True,
    ) -> ModelResult:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": think,
            "keep_alive": keep_alive,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "temperature": temperature,
                "seed": seed,
            },
        }
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
