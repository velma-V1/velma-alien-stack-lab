from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    status: str
    experiment_id: str = ""
    phase: str = ""
    family: str = ""
    model: str = ""
    quantization: str = ""
    context_limit: int = 0
    reasoning_budget: int = 0
    temperature: float = 0.0
    seed: int = 0
    representation: str = ""
    primitives: list[str] = field(default_factory=list)
    pass_order: list[str] = field(default_factory=list)
    source_hash: str = ""
    workspace_hash: str = ""
    derived_facts: list[dict[str, Any]] = field(default_factory=list)
    discarded_evidence: list[str] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    compiler_ms: float = 0.0
    prompt_tokens: int = 0
    eval_tokens: int = 0
    prompt_eval_ns: int = 0
    eval_ns: int = 0
    total_ns: int = 0
    load_ns: int = 0
    wall_ms: float = 0.0
    tokens_per_second: float = 0.0
    done_reason: str = ""
    hit_ceiling: bool = False
    thinking: str | None = None
    response: str | None = None
    prediction: str | None = None
    expected: str | None = None
    verified_success: bool | None = None
    deterministic_unique: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def append_jsonl(path: Path, record: RunRecord | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = record.to_dict() if isinstance(record, RunRecord) else record
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, sort_keys=True, ensure_ascii=False) + "\n")
