from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


JsonValue = Any


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Operation:
    operation_id: str
    capability: str
    payload: dict[str, JsonValue]

    def to_dict(self) -> dict[str, JsonValue]:
        return asdict(self)


@dataclass(frozen=True)
class TaskIR:
    task_id: str
    entities: tuple[dict[str, JsonValue], ...] = ()
    facts: tuple[dict[str, JsonValue], ...] = ()
    goals: tuple[dict[str, JsonValue], ...] = ()
    constraints: tuple[dict[str, JsonValue], ...] = ()
    relations: tuple[dict[str, JsonValue], ...] = ()
    actions: tuple[dict[str, JsonValue], ...] = ()
    resources: tuple[dict[str, JsonValue], ...] = ()
    objectives: tuple[dict[str, JsonValue], ...] = ()
    observations: tuple[dict[str, JsonValue], ...] = ()
    verification: tuple[dict[str, JsonValue], ...] = ()
    provenance: tuple[dict[str, JsonValue], ...] = ()
    required_capabilities: tuple[str, ...] = ()
    operations: tuple[Operation, ...] = ()

    def to_dict(self, *, include_required: bool = True) -> dict[str, JsonValue]:
        data = asdict(self)
        if not include_required:
            data.pop("required_capabilities", None)
        return data


@dataclass(frozen=True)
class EngineResult:
    ok: bool
    value: JsonValue = None
    certificate: dict[str, JsonValue] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return asdict(self)


@dataclass(frozen=True)
class AtlasCell:
    cell_id: str
    order: int
    phase: str
    world_id: str
    capabilities: tuple[str, ...]
    arm: str

    def to_dict(self) -> dict[str, JsonValue]:
        return asdict(self)
