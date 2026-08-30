from __future__ import annotations

import json
import math
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .context_engine_types import ContextDocument, ContextTask, EvidenceBundle, EvidenceItem


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def serialize_index_request(*, corpus_dir: str, corpus_identity: str, plane: str, index_id: str) -> dict[str, Any]:
    if plane not in {"raw", "normalized"}:
        raise ValueError("PLANE_INVALID")
    if not index_id.strip():
        raise ValueError("INDEX_ID_REQUIRED")
    return {
        "op": "index",
        "corpus_dir": str(corpus_dir),
        "corpus_identity": str(corpus_identity),
        "plane": plane,
        "index_id": index_id,
    }


def serialize_retrieve_request(
    task: ContextTask,
    *,
    plane: str,
    max_candidates: int,
    index_id: str | None = None,
) -> dict[str, Any]:
    if plane not in {"raw", "normalized"}:
        raise ValueError("PLANE_INVALID")
    request = {
        "op": "retrieve",
        "task_id": task.task_id,
        "question": task.question,
        "plane": plane,
        "max_candidates": int(max_candidates),
    }
    if index_id is not None:
        if not str(index_id).strip():
            raise ValueError("INDEX_ID_REQUIRED")
        request["index_id"] = str(index_id)
    return request


def serialize_update_request(*, index_id: str, source_id: str, document_path: str, version: str) -> dict[str, Any]:
    if not index_id.strip() or not source_id.strip() or not document_path.strip() or not version.strip():
        raise ValueError("UPDATE_FIELDS_REQUIRED")
    return {
        "op": "update",
        "index_id": index_id,
        "source_id": source_id,
        "document_path": document_path,
        "version": version,
    }


def serialize_answer_request(task: ContextTask, bundle: EvidenceBundle) -> dict[str, Any]:
    return {
        "op": "answer",
        "task_id": task.task_id,
        "question": task.question,
        "evidence_bundle": bundle.to_dict(),
    }


class ContextEngineAdapter:
    def identity(self) -> dict[str, Any]:
        raise NotImplementedError

    def index(self, *, corpus_dir: str, corpus_identity: str, plane: str, index_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def retrieve(self, task: ContextTask, *, plane: str, index_id: str | None = None) -> EvidenceBundle:
        raise NotImplementedError

    def update(self, *, index_id: str, source_id: str, document_path: str, version: str) -> dict[str, Any]:
        raise NotImplementedError


class BM25Adapter(ContextEngineAdapter):
    def __init__(self, *, system_id: str = "BM25_RAG", k1: float = 1.5, b: float = 0.75, max_candidates: int = 32) -> None:
        self.system_id = system_id
        self.k1 = float(k1)
        self.b = float(b)
        self.max_candidates = int(max_candidates)
        self._documents: tuple[ContextDocument, ...] = ()
        self._corpus_identity = ""
        self._index_id = ""
        self._doc_tokens: list[list[str]] = []
        self._df: Counter[str] = Counter()
        self._avgdl = 0.0

    def identity(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "method": "BM25",
            "k1": self.k1,
            "b": self.b,
            "evidence_kind": "DETERMINISTIC_BASELINE",
            "live": True,
            "pin": "alien-lab-bm25-v1",
        }

    def index_documents(self, documents: Iterable[ContextDocument], *, corpus_identity: str, index_id: str = "in-memory") -> None:
        self._documents = tuple(documents)
        self._corpus_identity = str(corpus_identity)
        self._index_id = str(index_id)
        self._doc_tokens = [_tokens(doc.text) for doc in self._documents]
        self._df = Counter()
        for tokens in self._doc_tokens:
            self._df.update(set(tokens))
        self._avgdl = (sum(len(tokens) for tokens in self._doc_tokens) / len(self._doc_tokens)) if self._doc_tokens else 0.0

    def index(self, *, corpus_dir: str, corpus_identity: str, plane: str, index_id: str) -> dict[str, Any]:
        root = Path(corpus_dir)
        manifest_path = root / "materialization.json"
        if not manifest_path.exists():
            raise ValueError("MATERIALIZATION_MANIFEST_MISSING")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        documents: list[ContextDocument] = []
        for row in manifest.get("documents") or []:
            source_id = str(row["source_id"])
            version = str(row.get("version") or "")
            filename = row["normalized_file"] if plane == "normalized" else row["raw_file"]
            path = root / plane / str(filename)
            if path.suffix.lower() not in {".txt", ".csv"}:
                continue
            documents.append(ContextDocument(source_id=source_id, text=path.read_text(encoding="utf-8"), version=version))
        self.index_documents(documents, corpus_identity=corpus_identity, index_id=index_id)
        return {"indexed_documents": len(documents), "index_id": index_id}

    def _score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not doc_tokens or not self._documents:
            return 0.0
        counts = Counter(doc_tokens)
        n_docs = len(self._documents)
        score = 0.0
        for token in query_tokens:
            df = self._df.get(token, 0)
            if df <= 0:
                continue
            idf = math.log(1.0 + ((n_docs - df + 0.5) / (df + 0.5)))
            tf = counts.get(token, 0)
            denom = tf + self.k1 * (1.0 - self.b + self.b * (len(doc_tokens) / self._avgdl if self._avgdl else 1.0))
            if denom:
                score += idf * ((tf * (self.k1 + 1.0)) / denom)
        return score

    def retrieve(self, task: ContextTask, *, plane: str, index_id: str | None = None) -> EvidenceBundle:
        if not self._documents:
            self.index_documents(task.normalized_documents if plane == "normalized" else task.raw_documents, corpus_identity="task-local")
        if index_id is not None and self._index_id and index_id != self._index_id:
            raise ValueError(f"BM25_INDEX_ID_MISMATCH:{index_id}:{self._index_id}")
        query_tokens = _tokens(task.question)
        scored = []
        for doc, tokens in zip(self._documents, self._doc_tokens):
            scored.append((self._score(query_tokens, tokens), doc.source_id, doc))
        scored.sort(key=lambda row: (-row[0], row[1]))
        items = tuple(
            EvidenceItem(
                source_id=doc.source_id,
                text=doc.text,
                rank=rank,
                score=score,
                version=doc.version,
                location=doc.location,
                provenance={"adapter": self.system_id},
            )
            for rank, (score, _, doc) in enumerate(scored[: self.max_candidates], start=1)
            if score > 0.0
        )
        return EvidenceBundle(
            task_id=task.task_id,
            system_id=self.system_id,
            corpus_identity=self._corpus_identity,
            plane=plane,
            items=items,
            trace={"method": "BM25", "k1": self.k1, "b": self.b, "index_id": self._index_id},
            query_metrics={},
        )

    def update(self, *, index_id: str, source_id: str, document_path: str, version: str) -> dict[str, Any]:
        if self._index_id and index_id != self._index_id:
            raise ValueError("BM25_INDEX_ID_MISMATCH")
        replacement_text = Path(document_path).read_text(encoding="utf-8")
        replaced = False
        documents: list[ContextDocument] = []
        for doc in self._documents:
            if doc.source_id == source_id:
                documents.append(ContextDocument(source_id=source_id, text=replacement_text, version=version, location=doc.location))
                replaced = True
            else:
                documents.append(doc)
        if not replaced:
            documents.append(ContextDocument(source_id=source_id, text=replacement_text, version=version))
        self.index_documents(documents, corpus_identity=self._corpus_identity, index_id=index_id)
        return {"updated": True, "source_id": source_id, "index_id": index_id}


class HybridRRFAdapter:
    @staticmethod
    def fuse_rankings(left: EvidenceBundle, right: EvidenceBundle, *, k: int = 60) -> EvidenceBundle:
        scores: dict[str, float] = {}
        exemplars: dict[str, EvidenceItem] = {}
        for bundle in (left, right):
            for item in bundle.items:
                scores[item.source_id] = scores.get(item.source_id, 0.0) + (1.0 / (k + item.rank))
                exemplars.setdefault(item.source_id, item)
        ordered = sorted(scores, key=lambda source_id: (-scores[source_id], source_id))
        items = tuple(
            EvidenceItem(
                source_id=source_id,
                text=exemplars[source_id].text,
                rank=rank,
                score=scores[source_id],
                version=exemplars[source_id].version,
                location=exemplars[source_id].location,
                provenance={"fusion": "RRF", "constituents": [left.system_id, right.system_id]},
            )
            for rank, source_id in enumerate(ordered, start=1)
        )
        return EvidenceBundle(
            task_id=left.task_id,
            system_id="HYBRID_RRF_RAG",
            corpus_identity=left.corpus_identity,
            plane=left.plane,
            items=items,
            trace={"rrf_k": k, "constituents": [left.system_id, right.system_id]},
            query_metrics={},
        )


class FixtureContextAdapter(ContextEngineAdapter):
    def __init__(self, *, system_id: str) -> None:
        self.system_id = system_id
        self._index_id = ""

    def identity(self) -> dict[str, Any]:
        return {"system_id": self.system_id, "evidence_kind": "FAKE_MECHANICS_ONLY", "live": False, "pin": "fixture-v1"}

    def index(self, *, corpus_dir: str, corpus_identity: str, plane: str, index_id: str) -> dict[str, Any]:
        self._index_id = index_id
        return {"indexed_documents": None, "index_id": index_id, "fixture": True}

    def retrieve(self, task: ContextTask, *, plane: str, index_id: str | None = None) -> EvidenceBundle:
        if index_id is not None and self._index_id and index_id != self._index_id:
            raise ValueError("FIXTURE_INDEX_ID_MISMATCH")
        documents = task.raw_documents if plane == "raw" else task.normalized_documents
        required = set(task.required_source_ids)
        ordered = sorted(documents, key=lambda doc: (doc.source_id not in required, doc.source_id))
        items = tuple(
            EvidenceItem(doc.source_id, doc.text, rank, version=doc.version, location=doc.location, provenance={"fixture": True})
            for rank, doc in enumerate(ordered, start=1)
            if task.answerable or rank > 1
        )
        if not task.answerable:
            items = ()
        return EvidenceBundle(task.task_id, self.system_id, "fixture-corpus", plane, items, {"fixture": True, "index_id": self._index_id}, {})

    def update(self, *, index_id: str, source_id: str, document_path: str, version: str) -> dict[str, Any]:
        return {"updated": True, "source_id": source_id, "index_id": index_id, "fixture": True}


@dataclass
class _JsonlProcessBase:
    command: tuple[str, ...]
    sealed_identity: dict[str, Any]
    timeout_seconds: float = 120.0

    def validate_identity(self, observed: dict[str, Any]) -> None:
        for key, expected in self.sealed_identity.items():
            if observed.get(key) != expected:
                raise ValueError(f"ADAPTER_IDENTITY_MISMATCH:{key}:expected={expected!r}:observed={observed.get(key)!r}")

    def _exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        completed = subprocess.run(
            self.command,
            input=json.dumps(request, sort_keys=True) + "\n",
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise OSError(f"ADAPTER_PROCESS_FAILED:{completed.returncode}:{completed.stderr.strip()}")
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            raise ValueError("ADAPTER_PROTOCOL_RESPONSE_COUNT")
        response = json.loads(lines[0])
        if not response.get("ok"):
            raise OSError(f"ADAPTER_PROTOCOL_ERROR:{response.get('error')}")
        self.validate_identity(response.get("adapter_identity") or {})
        return response

    def identity(self) -> dict[str, Any]:
        response = self._exchange({"op": "identity"})
        return dict(response["adapter_identity"])


@dataclass
class JsonlSubprocessAdapter(_JsonlProcessBase, ContextEngineAdapter):
    def index(self, *, corpus_dir: str, corpus_identity: str, plane: str, index_id: str) -> dict[str, Any]:
        response = self._exchange(
            serialize_index_request(corpus_dir=corpus_dir, corpus_identity=corpus_identity, plane=plane, index_id=index_id)
        )
        return dict(response.get("index_metrics") or {})

    def retrieve(self, task: ContextTask, *, plane: str, index_id: str | None = None) -> EvidenceBundle:
        response = self._exchange(serialize_retrieve_request(task, plane=plane, max_candidates=32, index_id=index_id))
        payload = response.get("evidence_bundle") or {}
        items = tuple(EvidenceItem(**item) for item in payload.get("items", ()))
        bundle = EvidenceBundle(
            task_id=str(payload["task_id"]),
            system_id=str(payload["system_id"]),
            corpus_identity=str(payload["corpus_identity"]),
            plane=str(payload["plane"]),
            items=items,
            trace=dict(payload.get("trace") or {}),
            query_metrics=dict(payload.get("query_metrics") or {}),
        )
        if bundle.task_id != task.task_id:
            raise ValueError("ADAPTER_TASK_ID_MISMATCH")
        if bundle.system_id != str(self.sealed_identity.get("system_id")):
            raise ValueError("ADAPTER_SYSTEM_ID_MISMATCH")
        return bundle

    def update(self, *, index_id: str, source_id: str, document_path: str, version: str) -> dict[str, Any]:
        response = self._exchange(
            serialize_update_request(index_id=index_id, source_id=source_id, document_path=document_path, version=version)
        )
        return dict(response.get("update_metrics") or {})


@dataclass
class JsonlAnswerSystemAdapter(_JsonlProcessBase):
    def answer(self, task: ContextTask, bundle: EvidenceBundle) -> dict[str, Any]:
        response = self._exchange(serialize_answer_request(task, bundle))
        payload = response.get("answer_payload")
        if not isinstance(payload, dict):
            raise ValueError("ANSWER_ADAPTER_PAYLOAD_MISSING")
        if set(payload) != {"answer", "citations", "abstain"}:
            raise ValueError("ANSWER_ADAPTER_SCHEMA_MISMATCH")
        return {
            "answer_payload": payload,
            "metrics": dict(response.get("answer_metrics") or {}),
            "evidence_kind": str(response.get("evidence_kind") or "LIVE_SYSTEM_EVIDENCE"),
        }
