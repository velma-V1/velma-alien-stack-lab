from __future__ import annotations

import json
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFont

from .computational_atlas_live_types import ModelRequest
from .computational_atlas_providers import ModelProvider, parse_model_json
from .computational_atlas_types import stable_hash
from .context_engine_scoring import budget_evidence
from .context_engine_types import (
    ADVANCED_PINS,
    ADVANCED_SYSTEMS,
    ANSWER_CONTEXT_UTF8_BYTES,
    ANSWER_MAX_OUTPUT_TOKENS,
    RETRIEVAL_ARMS,
    ContextCorpus,
    ContextDocument,
    ContextTask,
    EvidenceBundle,
)


ANSWER_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": ["string", "null"]},
        "citations": {"type": "array", "items": {"type": "string"}},
        "abstain": {"type": "boolean"},
    },
    "required": ["answer", "citations", "abstain"],
    "additionalProperties": False,
}

ANSWER_SYSTEM_PROMPT = (
    "You are the common answer stage for a controlled retrieval experiment. "
    "Use only the supplied evidence. If the evidence is insufficient to answer the question, abstain. "
    "Return only the requested JSON object. Citations must be source IDs from the supplied evidence."
)


@dataclass(frozen=True)
class AnswerModelSpec:
    model_id: str
    endpoint: str
    context_limit: int

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AnswerModelSpec":
        model_id = str(payload.get("model_id") or "").strip()
        endpoint = str(payload.get("endpoint") or "").strip().rstrip("/")
        context_limit = payload.get("context_limit")
        if not model_id or not endpoint:
            raise ValueError("ANSWER_MODEL_IDENTITY_REQUIRED")
        if not isinstance(context_limit, int) or isinstance(context_limit, bool) or context_limit <= 0:
            raise ValueError("ANSWER_MODEL_CONTEXT_LIMIT_REQUIRED")
        return cls(model_id=model_id, endpoint=endpoint, context_limit=context_limit)


@dataclass(frozen=True)
class AdapterSpec:
    system_id: str
    command: tuple[str, ...]
    pin: str

    @classmethod
    def from_dict(cls, system_id: str, payload: Mapping[str, Any]) -> "AdapterSpec":
        command_raw = payload.get("command")
        if not isinstance(command_raw, list) or not command_raw or not all(isinstance(part, str) and part.strip() for part in command_raw):
            raise ValueError(f"ADAPTER_COMMAND_REQUIRED:{system_id}")
        pin = str(payload.get("pin") or "").strip()
        if not pin:
            raise ValueError(f"ADAPTER_PIN_REQUIRED:{system_id}")
        return cls(system_id=system_id, command=tuple(command_raw), pin=pin)


@dataclass(frozen=True)
class Live0101Config:
    answer_model: AnswerModelSpec
    retrieval_adapter_specs: dict[str, AdapterSpec]
    advanced_adapter_specs: dict[str, AdapterSpec]
    velma_adapter: AdapterSpec

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Live0101Config":
        answer_model = AnswerModelSpec.from_dict(payload.get("answer_model") or {})
        retrieval_raw = payload.get("retrieval_adapters")
        if not isinstance(retrieval_raw, dict):
            raise ValueError("RETRIEVAL_ADAPTERS_REQUIRED")

        required = set(ADVANCED_SYSTEMS) | {"DENSE_VECTOR_RAG"}
        missing = required - set(retrieval_raw)
        extra = set(retrieval_raw) - required
        if missing:
            raise ValueError(f"RETRIEVAL_ADAPTERS_MISSING:{sorted(missing)}")
        if extra:
            raise ValueError(f"RETRIEVAL_ADAPTERS_UNEXPECTED:{sorted(extra)}")

        retrieval_specs = {
            system_id: AdapterSpec.from_dict(system_id, retrieval_raw[system_id])
            for system_id in sorted(required)
        }
        for system_id, expected_pin in ADVANCED_PINS.items():
            if retrieval_specs[system_id].pin != expected_pin:
                raise ValueError(
                    f"FROZEN_ADAPTER_PIN_MISMATCH:{system_id}:expected={expected_pin}:observed={retrieval_specs[system_id].pin}"
                )

        velma_raw = payload.get("velma_adapter")
        if not isinstance(velma_raw, dict):
            raise ValueError("VELMA_ADAPTER_REQUIRED")
        velma = AdapterSpec.from_dict("VELMA", velma_raw)

        advanced = {system_id: retrieval_specs[system_id] for system_id in ADVANCED_SYSTEMS}
        return cls(
            answer_model=answer_model,
            retrieval_adapter_specs=retrieval_specs,
            advanced_adapter_specs=advanced,
            velma_adapter=velma,
        )

    @classmethod
    def from_json(cls, path: Path) -> "Live0101Config":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_model": {
                "model_id": self.answer_model.model_id,
                "endpoint": self.answer_model.endpoint,
                "context_limit": self.answer_model.context_limit,
            },
            "retrieval_adapters": {
                system_id: {"command": list(spec.command), "pin": spec.pin}
                for system_id, spec in sorted(self.retrieval_adapter_specs.items())
            },
            "velma_adapter": {"command": list(self.velma_adapter.command), "pin": self.velma_adapter.pin},
        }

    def config_hash(self) -> str:
        return stable_hash(self.to_dict())


def _all_documents(corpus: ContextCorpus, *, include_transfer: bool, plane: str) -> tuple[ContextDocument, ...]:
    by_id: dict[str, ContextDocument] = {}
    for task in corpus.tasks:
        if not include_transfer and task.split == "VELMA_TRANSFER":
            continue
        documents = task.raw_documents if plane == "raw" else task.normalized_documents
        for doc in documents:
            previous = by_id.get(doc.source_id)
            if previous is not None and previous.to_dict() != doc.to_dict():
                raise ValueError(f"SOURCE_ID_COLLISION:{doc.source_id}")
            by_id[doc.source_id] = doc
    return tuple(by_id[source_id] for source_id in sorted(by_id))


def _safe_write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _render_text_image(text: str, path: Path, *, width: int = 1500, height: int = 1100) -> None:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    wrapped: list[str] = []
    for paragraph in text.splitlines() or [text]:
        wrapped.extend(textwrap.wrap(paragraph, width=100) or [""])
    draw.multiline_text((60, 60), "\n".join(wrapped[:80]), fill="black", font=font, spacing=8)
    image.save(path)


def _render_pdf(text: str, path: Path) -> None:
    pages: list[Image.Image] = []
    paragraphs = textwrap.wrap(text, width=105) or [""]
    chunks = [paragraphs[i : i + 65] for i in range(0, len(paragraphs), 65)] or [[""]]
    font = ImageFont.load_default()
    for page_number, lines in enumerate(chunks, start=1):
        image = Image.new("RGB", (1654, 2339), "white")
        draw = ImageDraw.Draw(image)
        draw.text((80, 60), f"Document page {page_number}", fill="black", font=font)
        draw.multiline_text((80, 120), "\n".join(lines), fill="black", font=font, spacing=10)
        pages.append(image)
    first, *rest = pages
    first.save(path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    for page in pages:
        page.close()


def _materialize_raw_document(doc: ContextDocument, directory: Path) -> str:
    if doc.modality == "table":
        path = directory / f"{doc.source_id}.csv"
        text = doc.text.replace("|", ",").strip(" ,\n")
        _safe_write_text(path, text)
    elif doc.modality == "image":
        path = directory / f"{doc.source_id}.png"
        _render_text_image(doc.text, path)
    elif doc.modality == "pdf-layout":
        path = directory / f"{doc.source_id}.pdf"
        _render_pdf(doc.text, path)
    else:
        path = directory / f"{doc.source_id}.txt"
        _safe_write_text(path, doc.text)
    return path.name


def materialize_corpus(corpus: ContextCorpus, root: Path, *, include_transfer: bool) -> dict[str, Any]:
    root = Path(root)
    raw_dir = root / "raw"
    normalized_dir = root / "normalized"
    if root.exists():
        shutil.rmtree(root)
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    raw_documents = _all_documents(corpus, include_transfer=include_transfer, plane="raw")
    normalized_documents = _all_documents(corpus, include_transfer=include_transfer, plane="normalized")
    if {doc.source_id for doc in raw_documents} != {doc.source_id for doc in normalized_documents}:
        raise ValueError("RAW_NORMALIZED_SOURCE_SET_MISMATCH")

    rows: list[dict[str, Any]] = []
    normalized_by_id = {doc.source_id: doc for doc in normalized_documents}
    for raw_doc in raw_documents:
        normalized_doc = normalized_by_id[raw_doc.source_id]
        raw_name = _materialize_raw_document(raw_doc, raw_dir)
        normalized_name = f"{normalized_doc.source_id}.txt"
        _safe_write_text(normalized_dir / normalized_name, normalized_doc.text)
        rows.append(
            {
                "source_id": raw_doc.source_id,
                "version": raw_doc.version,
                "raw_file": raw_name,
                "normalized_file": normalized_name,
                "raw_modality": raw_doc.modality,
            }
        )

    manifest = {
        "corpus_hash": corpus.corpus_hash,
        "include_transfer": bool(include_transfer),
        "document_count": len(rows),
        "source_ids": [row["source_id"] for row in rows],
        "documents": rows,
    }
    (root / "materialization.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_answer_prompt(task: ContextTask, delivered_bundle: EvidenceBundle) -> str:
    evidence_blocks: list[str] = []
    for item in sorted(delivered_bundle.items, key=lambda value: (value.rank, value.source_id)):
        evidence_blocks.append(f"[SOURCE {item.source_id}]\n{item.text}")
    evidence = "\n\n".join(evidence_blocks) if evidence_blocks else "(no evidence supplied)"
    return f"QUESTION:\n{task.question}\n\nEVIDENCE:\n{evidence}\n"


def answer_with_provider(task: ContextTask, bundle: EvidenceBundle, provider: ModelProvider) -> dict[str, Any]:
    delivered = budget_evidence(bundle, max_utf8_bytes=ANSWER_CONTEXT_UTF8_BYTES)
    request = ModelRequest(
        request_id=stable_hash(["010.1-answer", task.task_id, delivered.to_dict()])[:24],
        prompt=build_answer_prompt(task, delivered),
        json_schema=ANSWER_JSON_SCHEMA,
        max_output_tokens=ANSWER_MAX_OUTPUT_TOKENS,
        system=ANSWER_SYSTEM_PROMPT,
    )
    response = provider.complete(request)
    if not response.ok:
        return {
            "ok": False,
            "answer_payload": None,
            "model_calls": response.model_calls,
            "prompt_tokens": response.prompt_tokens,
            "output_tokens": response.output_tokens,
            "duration_ms": response.duration_ms,
            "error_kind": response.error_kind,
            "error": response.error,
            "evidence_kind": response.evidence_kind,
            "delivered_bundle": delivered.to_dict(),
        }
    parsed = parse_model_json(response)
    if not isinstance(parsed, dict):
        raise ValueError("ANSWER_PAYLOAD_NOT_OBJECT")
    if set(parsed) != {"answer", "citations", "abstain"}:
        raise ValueError("ANSWER_PAYLOAD_SCHEMA_MISMATCH")
    if not isinstance(parsed.get("citations"), list) or not isinstance(parsed.get("abstain"), bool):
        raise ValueError("ANSWER_PAYLOAD_SCHEMA_MISMATCH")
    return {
        "ok": True,
        "answer_payload": parsed,
        "model_calls": response.model_calls,
        "prompt_tokens": response.prompt_tokens,
        "output_tokens": response.output_tokens,
        "duration_ms": response.duration_ms,
        "error_kind": None,
        "error": None,
        "evidence_kind": response.evidence_kind,
        "delivered_bundle": delivered.to_dict(),
    }


def _identity_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    reader = getattr(value, "identity", None)
    if not callable(reader):
        raise ValueError("ADAPTER_IDENTITY_UNAVAILABLE")
    observed = reader()
    if not isinstance(observed, dict):
        raise ValueError("ADAPTER_IDENTITY_NOT_OBJECT")
    return dict(observed)


def validate_candidate_identities(
    adapters: Mapping[str, Any],
    *,
    required_pins: Mapping[str, str],
    allow_fixture: bool,
) -> dict[str, Any]:
    if set(adapters) != set(required_pins):
        raise ValueError("CANDIDATE_SET_MISMATCH")
    validated: dict[str, dict[str, Any]] = {}
    for system_id, required_pin in required_pins.items():
        observed = _identity_payload(adapters[system_id])
        if observed.get("system_id") != system_id:
            raise ValueError(f"CANDIDATE_IDENTITY_MISMATCH:{system_id}")
        if observed.get("pin") != required_pin:
            raise ValueError(f"CANDIDATE_PIN_MISMATCH:{system_id}")
        if not allow_fixture and observed.get("live") is not True:
            raise ValueError(f"CANDIDATE_NOT_LIVE:{system_id}")
        if not allow_fixture and observed.get("evidence_kind") == "FAKE_MECHANICS_ONLY":
            raise ValueError(f"CANDIDATE_FIXTURE_FORBIDDEN:{system_id}")
        validated[system_id] = observed
    return {"validated": len(validated), "identities": validated}


def select_best_standalone(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise ValueError("STANDALONE_SELECTION_REQUIRES_ROWS")
    if any(row.get("split") not in {"DISCOVERY", "CONFIRMATORY"} for row in rows):
        raise ValueError("PRETRANSFER_ROWS_ONLY")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        arm = str(row.get("arm") or "")
        if arm not in RETRIEVAL_ARMS:
            continue
        grouped.setdefault(arm, []).append(row)
    if not grouped:
        raise ValueError("NO_CONTEXT_ARMS_TO_SELECT")

    def key(item: tuple[str, list[dict[str, Any]]]) -> tuple[Any, ...]:
        arm, arm_rows = item
        valid = [row for row in arm_rows if row.get("score") is not None]
        if not valid:
            return (-1.0, -1.0, float("-inf"), arm)
        success = sum(int(row.get("score") == 1) for row in valid) / len(valid)
        silent_wrong = sum(int(bool(row.get("silent_wrong"))) for row in valid) / len(valid)
        measured_costs = [float(row["cost"]) for row in valid if row.get("cost") is not None]
        mean_cost = (sum(measured_costs) / len(measured_costs)) if measured_costs else float("inf")
        return (success, -silent_wrong, -mean_cost, arm)

    return max(grouped.items(), key=key)[0]
