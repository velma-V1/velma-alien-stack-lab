from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol

from .computational_atlas_live_types import ModelRequest, ModelResponse, RunIdentity
from .computational_atlas_types import stable_hash


class ModelProvider(Protocol):
    model_id: str
    endpoint: str
    provider_kind: str
    supports_structured_output: bool
    transport_retries_total: int

    def complete(self, request: ModelRequest) -> ModelResponse: ...


def _parse_json_text(text: str) -> Any:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
        if raw.lower().startswith("json\n"):
            raw = raw[5:].strip()
    return json.loads(raw)


def parse_model_json(response: ModelResponse) -> Any:
    """Parse model JSON identically regardless of experimental arm."""
    if response.parsed_json is not None:
        return response.parsed_json
    return _parse_json_text(response.text)


def seal_run_identity(identity: RunIdentity) -> str:
    return stable_hash(identity.to_dict())


class FakeProvider:
    provider_kind = "fake"
    supports_structured_output = True

    def __init__(self, model_id: str, scripted: list[Any]):
        self.model_id = model_id
        self.endpoint = "fake://experiment-010"
        self.transport_retries_total = 0
        self._scripted = list(scripted)
        self._index = 0

    def complete(self, request: ModelRequest) -> ModelResponse:
        if self._index >= len(self._scripted):
            return ModelResponse(ok=False, text="", model_calls=1, error_kind="FAKE_SCRIPT_EXHAUSTED", error="no scripted response", evidence_kind="FAKE_MECHANICS_ONLY")
        item = self._scripted[self._index]
        self._index += 1
        if isinstance(item, Exception):
            return ModelResponse(ok=False, text="", model_calls=1, error_kind="FAKE_ERROR", error=str(item), evidence_kind="FAKE_MECHANICS_ONLY")
        if isinstance(item, str):
            text = item
            try:
                parsed = _parse_json_text(text)
            except Exception:
                parsed = None
        else:
            parsed = item
            text = json.dumps(item, sort_keys=True)
        return ModelResponse(ok=True, text=text, parsed_json=parsed, model_calls=1, evidence_kind="FAKE_MECHANICS_ONLY", raw={"scripted_index": self._index - 1})


class _HTTPProviderBase:
    provider_kind = "http"
    supports_structured_output = False

    def __init__(self, *, model_id: str, endpoint: str, timeout: float = 180.0, transport: Callable[[urllib.request.Request, float], bytes] | None = None):
        self.model_id = model_id
        self.endpoint = endpoint.rstrip("/")
        self.timeout = float(timeout)
        self.transport_retries_total = 0
        self._transport = transport or self._default_transport

    @staticmethod
    def _default_transport(request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    def _request_json(self, request: urllib.request.Request) -> tuple[dict[str, Any] | None, str | None, float, int]:
        start = time.perf_counter()
        last_error: str | None = None
        for attempt in range(3):
            try:
                raw = self._transport(request, self.timeout)
                elapsed = (time.perf_counter() - start) * 1000.0
                return json.loads(raw.decode("utf-8")), None, elapsed, attempt
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt >= 2:
                    break
        return None, last_error, (time.perf_counter() - start) * 1000.0, 2

    def _get(self, path: str, headers: dict[str, str] | None = None) -> tuple[dict[str, Any] | None, str | None, float, int]:
        request = urllib.request.Request(self.endpoint + path, headers=headers or {}, method="GET")
        return self._request_json(request)

    def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str]) -> tuple[dict[str, Any] | None, str | None, float, int]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(self.endpoint + path, data=body, headers=headers, method="POST")
        return self._request_json(request)


class OllamaProvider(_HTTPProviderBase):
    provider_kind = "ollama"
    supports_structured_output = True

    @staticmethod
    def default_path() -> str:
        return "/api/chat"

    def server_version(self) -> str:
        data, transport_error, _, _ = self._get("/api/version", {"Accept": "application/json"})
        if data is None:
            raise ValueError(f"PROVIDER_VERSION_UNAVAILABLE:{transport_error}")
        version = str(data.get("version") or "").strip()
        if not version:
            raise ValueError("PROVIDER_VERSION_UNAVAILABLE:missing_version")
        return version

    def complete(self, request: ModelRequest) -> ModelResponse:
        message: dict[str, Any] = {"role": "user", "content": request.prompt}
        if request.images:
            message["images"] = [image.base64_data for image in request.images]
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [message],
            "stream": False,
            "options": {"num_predict": request.max_output_tokens},
        }
        if request.json_schema is not None:
            payload["format"] = request.json_schema
        if request.tools:
            payload["tools"] = list(request.tools)
        data, transport_error, elapsed, retries = self._post(self.default_path(), payload, {"Content-Type": "application/json"})
        self.transport_retries_total += retries
        if data is None:
            return ModelResponse(ok=False, text="", model_calls=1, duration_ms=elapsed, error_kind="TRANSPORT", error=transport_error, transport_retries=retries)
        message_data = data.get("message") or {}
        text = str(message_data.get("content") or "")
        parsed = None
        if request.json_schema is not None:
            try:
                parsed = _parse_json_text(text)
            except Exception as exc:
                return ModelResponse(ok=False, text=text, model_calls=1, prompt_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"), duration_ms=elapsed, stop_reason=data.get("done_reason"), error_kind="MALFORMED_OUTPUT", error=str(exc), transport_retries=retries, raw=data)
        return ModelResponse(ok=True, text=text, parsed_json=parsed, model_calls=1, prompt_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"), duration_ms=elapsed, stop_reason=data.get("done_reason"), transport_retries=retries, raw=data)


class AnthropicMessagesProvider(_HTTPProviderBase):
    provider_kind = "anthropic"
    supports_structured_output = False

    def __init__(self, *, model_id: str, endpoint: str = "https://api.anthropic.com", api_key: str, anthropic_version: str = "2023-06-01", timeout: float = 180.0, transport: Callable[[urllib.request.Request, float], bytes] | None = None):
        super().__init__(model_id=model_id, endpoint=endpoint, timeout=timeout, transport=transport)
        self.api_key = api_key
        self.anthropic_version = anthropic_version

    @staticmethod
    def default_path() -> str:
        return "/v1/messages"

    def complete(self, request: ModelRequest) -> ModelResponse:
        user_content: list[dict[str, Any]] = []
        for image in request.images:
            user_content.append({"type": "image", "source": {"type": "base64", "media_type": image.media_type, "data": image.base64_data}})
        user_content.append({"type": "text", "text": request.prompt})
        payload: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": request.max_output_tokens,
            "messages": [{"role": "user", "content": user_content}],
        }
        if request.system:
            payload["system"] = request.system
        if request.tools:
            payload["tools"] = list(request.tools)
        data, transport_error, elapsed, retries = self._post(
            self.default_path(),
            payload,
            {"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": self.anthropic_version},
        )
        self.transport_retries_total += retries
        if data is None:
            return ModelResponse(ok=False, text="", model_calls=1, duration_ms=elapsed, error_kind="TRANSPORT", error=transport_error, transport_retries=retries)
        stop_reason = data.get("stop_reason")
        blocks = data.get("content") or []
        text = "\n".join(str(block.get("text", "")) for block in blocks if block.get("type") == "text").strip()
        usage = data.get("usage") or {}
        if stop_reason == "refusal":
            return ModelResponse(ok=False, text=text, model_calls=1, prompt_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"), duration_ms=elapsed, stop_reason=stop_reason, error_kind="REFUSAL", error="provider refusal", transport_retries=retries, raw=data)
        parsed = None
        if request.json_schema is not None:
            try:
                parsed = _parse_json_text(text)
            except Exception as exc:
                return ModelResponse(ok=False, text=text, model_calls=1, prompt_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"), duration_ms=elapsed, stop_reason=stop_reason, error_kind="MALFORMED_OUTPUT", error=str(exc), transport_retries=retries, raw=data)
        return ModelResponse(ok=True, text=text, parsed_json=parsed, model_calls=1, prompt_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"), duration_ms=elapsed, stop_reason=stop_reason, transport_retries=retries, raw=data)
