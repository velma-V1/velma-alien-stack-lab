from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRecord:
    record_id: str
    key: str
    value: str
    authority: int
    revision: int
    scope: str
    kind: str = "state"
    raw: str = ""


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    active: bool
    scope: str
    raw: str = ""


@dataclass(frozen=True)
class CompilerInput:
    task_id: str
    family: str
    target_scope: str
    target_key: str
    entry: str
    sources: tuple[SourceRecord, ...]
    edges: tuple[Edge, ...]
    procedure_rules: tuple[str, ...]


@dataclass(frozen=True)
class Task:
    task_id: str
    family: str
    target_scope: str
    target_key: str
    entry: str
    sources: tuple[SourceRecord, ...]
    edges: tuple[Edge, ...]
    procedure_rules: tuple[str, ...]
    question: str
    choices: dict[str, str]

    def compiler_view(self) -> CompilerInput:
        return CompilerInput(
            task_id=self.task_id,
            family=self.family,
            target_scope=self.target_scope,
            target_key=self.target_key,
            entry=self.entry,
            sources=self.sources,
            edges=self.edges,
            procedure_rules=self.procedure_rules,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskSet:
    discovery: tuple[Task, ...]
    transfer: tuple[Task, ...]
    challenge: tuple[Task, ...]

    def all_tasks(self) -> tuple[Task, ...]:
        seen: dict[str, Task] = {}
        for task in (*self.discovery, *self.transfer, *self.challenge):
            seen.setdefault(task.task_id, task)
        return tuple(seen.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery": [t.to_dict() for t in self.discovery],
            "transfer": [t.to_dict() for t in self.transfer],
            "challenge": [t.to_dict() for t in self.challenge],
        }


@dataclass(frozen=True)
class SealedAnswers:
    answers: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"answers": self.answers}


@dataclass
class Derivation:
    pass_name: str
    output_type: str
    output: Any
    input_ids: list[str] = field(default_factory=list)
    rule: str = ""


@dataclass
class Workspace:
    task_id: str
    evidence_ids: list[str]
    edge_ids: list[str]
    current_state: dict[str, str] = field(default_factory=dict)
    active_path: list[str] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    memory_deltas: list[dict[str, Any]] = field(default_factory=list)
    discarded_evidence: list[str] = field(default_factory=list)
    derivations: list[Derivation] = field(default_factory=list)
    pass_order: list[str] = field(default_factory=list)
    pass_timings_ms: dict[str, float] = field(default_factory=dict)
    fused_relations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
