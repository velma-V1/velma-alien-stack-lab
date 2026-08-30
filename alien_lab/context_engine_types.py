from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .computational_atlas_types import stable_hash


EXPERIMENT = "010.1-context-engine-causal-attribution"
CORPUS_SEED = 20261001
ANSWER_CONTEXT_UTF8_BYTES = 16384
ANSWER_MAX_OUTPUT_TOKENS = 512
RRF_K = 60

ADVANCED_SYSTEMS = (
    "RAGFLOW_FULL",
    "PAGEINDEX_TREE",
    "MICROSOFT_GRAPHRAG",
    "COLBERT_LATE_INTERACTION",
    "HIPPORAG_PPR",
    "SERVIETTE_LIVE_RAG",
)
CONVENTIONAL_RETRIEVAL_ARMS = ("BM25_RAG", "DENSE_VECTOR_RAG", "HYBRID_RRF_RAG")
RETRIEVAL_ARMS = CONVENTIONAL_RETRIEVAL_ARMS + ADVANCED_SYSTEMS
STANDALONE_ARMS = ("MODEL_ONLY",) + CONVENTIONAL_RETRIEVAL_ARMS + ADVANCED_SYSTEMS + ("ORACLE_CONTEXT",)
STRATA = (
    "SINGLE_HOP_TEXT",
    "TABLE_STRUCTURED",
    "LONG_LAYOUT_PDF",
    "SCANNED_MULTIMODAL",
    "CROSS_DOC_MULTI_HOP",
    "RELATIONAL_GLOBAL",
    "CONTRADICTION_VERSION_NO_ANSWER",
    "DYNAMIC_UPDATE_FRESHNESS",
)
SPLITS = ("DISCOVERY", "CONFIRMATORY", "VELMA_TRANSFER")
ADVANCED_PINS = {
    "RAGFLOW_FULL": "v0.27.1",
    "PAGEINDEX_TREE": "9fee239b174fcc205fec28df105e519ac7171522",
    "MICROSOFT_GRAPHRAG": "v3.1.2",
    "COLBERT_LATE_INTERACTION": "cc4f3dc91c0b45d2d08c251d9d95178285c65f1c",
    "HIPPORAG_PPR": "2f52a86dd04e4633703bd2fb3bb6a37683ac3cfb",
    "SERVIETTE_LIVE_RAG": "800c874621c22dcdb9c29cf20bcd5205551800eb",
}


@dataclass(frozen=True)
class ContextDocument:
    source_id: str
    text: str
    version: str = "V1"
    location: str | None = None
    modality: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextTask:
    task_id: str
    stratum: str
    split: str
    question: str
    expected_answer: str | None
    required_source_ids: tuple[str, ...]
    raw_documents: tuple[ContextDocument, ...]
    normalized_documents: tuple[ContextDocument, ...]
    answerable: bool
    required_versions: dict[str, str] = field(default_factory=dict)
    freshness_revision: dict[str, Any] | None = None

    def to_dict(self, *, include_sealed: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if not include_sealed:
            payload.pop("expected_answer", None)
            payload.pop("required_source_ids", None)
            payload.pop("required_versions", None)
            payload.pop("freshness_revision", None)
        return payload


@dataclass(frozen=True)
class ContextCorpus:
    seed: int
    tasks: tuple[ContextTask, ...]
    corpus_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {"seed": self.seed, "tasks": [task.to_dict() for task in self.tasks], "corpus_hash": self.corpus_hash}


@dataclass(frozen=True)
class EvidenceItem:
    source_id: str
    text: str
    rank: int
    score: float | None = None
    version: str | None = None
    location: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    task_id: str
    system_id: str
    corpus_identity: str
    plane: str
    items: tuple[EvidenceItem, ...]
    trace: dict[str, Any] = field(default_factory=dict)
    query_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "system_id": self.system_id,
            "corpus_identity": self.corpus_identity,
            "plane": self.plane,
            "items": [item.to_dict() for item in self.items],
            "trace": self.trace,
            "query_metrics": self.query_metrics,
        }


@dataclass(frozen=True)
class ContextCell:
    cell_id: str
    order: int
    stage: str
    task_id: str
    arm: str
    plane: str
    topology_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalScore:
    required_recall: float
    relevant_precision: float
    first_relevant_rank: int | None
    reciprocal_rank: float
    context_sufficient: bool
    wrong_version_count: int
    stale_selected: bool
    no_answer_contamination: int
    retrieved_source_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnswerScore:
    score: int
    citation_correct: bool
    correct_abstention: bool
    unnecessary_abstention: bool
    silent_wrong: bool
    normalized_answer: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_cell_id(*parts: Any) -> str:
    return stable_hash([str(part) for part in parts])[:24]
