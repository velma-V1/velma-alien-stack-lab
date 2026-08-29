from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveImage:
    media_type: str
    base64_data: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelRequest:
    request_id: str
    prompt: str
    json_schema: dict[str, Any] | None = None
    images: tuple[LiveImage, ...] = ()
    max_output_tokens: int = 2048
    tools: tuple[dict[str, Any], ...] = ()
    system: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    ok: bool
    text: str
    parsed_json: Any = None
    model_calls: int = 1
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: float | None = None
    stop_reason: str | None = None
    error_kind: str | None = None
    error: str | None = None
    evidence_kind: str = "LIVE_MODEL_EVIDENCE"
    transport_retries: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunIdentity:
    experiment: str
    profile: str
    system_version: str
    provider_kind: str
    model_id: str
    endpoint: str
    generation_contract: dict[str, Any]
    prompt_contract_hash: str
    model_digest: str | None = None
    provider_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveCell:
    cell_id: str
    order: int
    phase: str
    seed: int
    arm: str
    world_index: int | None = None
    world_id: str | None = None
    representation: str | None = None
    condition: str | None = None
    lineage_index: int | None = None
    stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
