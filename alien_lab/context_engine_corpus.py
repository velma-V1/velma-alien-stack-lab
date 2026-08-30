from __future__ import annotations

import random
from typing import Any

from .computational_atlas_types import stable_hash
from .context_engine_types import ContextCorpus, ContextDocument, ContextTask, STRATA


def _source_id(seed: int, stratum_index: int, task_index: int, doc_index: int) -> str:
    return "src-" + stable_hash([seed, stratum_index, task_index, doc_index])[:12]


def _task_id(seed: int, stratum_index: int, task_index: int) -> str:
    return "ctx-" + stable_hash(["task", seed, stratum_index, task_index])[:16]


def _split(local_index: int) -> str:
    if local_index < 6:
        return "DISCOVERY"
    if local_index < 9:
        return "CONFIRMATORY"
    return "VELMA_TRANSFER"


def _make_documents(
    *,
    seed: int,
    stratum_index: int,
    task_index: int,
    token: str,
    previous_token: str,
    answerable: bool,
    stratum: str,
) -> tuple[tuple[ContextDocument, ...], tuple[ContextDocument, ...], tuple[str, ...], dict[str, str], dict[str, Any] | None]:
    ids = tuple(_source_id(seed, stratum_index, task_index, i) for i in range(4))
    current = ids[0]
    stale = ids[1]
    normalized_texts: list[tuple[str, str, str]] = [
        (current, f"Registry record: the current authorization value for unit Orion-{task_index:02d} is {token}.", "V2"),
        (stale, f"Archived registry copy: authorization value for unit Orion-{task_index:02d} was {previous_token}.", "V1"),
        (ids[2], f"Maintenance bulletin for unit Orion-{task_index:02d}; inspection class {100 + task_index}.", "V2"),
        (ids[3], f"Inventory memo for warehouse item {200 + task_index}; no authorization value is stated.", "V2"),
    ]

    if stratum == "TABLE_STRUCTURED":
        normalized_texts[0] = (current, f"unit,value,status\nOrion-{task_index:02d},{token},current", "V2")
    elif stratum == "LONG_LAYOUT_PDF":
        normalized_texts[0] = (current, ("Section preface. " * 80) + f"Appendix C states current authorization {token} for Orion-{task_index:02d}.", "V2")
    elif stratum == "SCANNED_MULTIMODAL":
        normalized_texts[0] = (current, f"Scanned form transcription: ORION {task_index:02d} CURRENT AUTH {token}", "V2")
    elif stratum == "CROSS_DOC_MULTI_HOP":
        normalized_texts[0] = (current, f"Unit Orion-{task_index:02d} maps to locker K-{task_index:03d}.", "V2")
        normalized_texts[2] = (ids[2], f"Locker K-{task_index:03d} contains authorization value {token}.", "V2")
    elif stratum == "RELATIONAL_GLOBAL":
        normalized_texts[0] = (current, f"Node Orion-{task_index:02d} reports to cluster C-{task_index % 5}; cluster token is stored in source {ids[2]}.", "V2")
        normalized_texts[2] = (ids[2], f"Cluster C-{task_index % 5} current authorization value is {token}.", "V2")
    elif stratum == "CONTRADICTION_VERSION_NO_ANSWER" and not answerable:
        normalized_texts[0] = (current, f"Current registry for Orion-{task_index:02d} explicitly omits the authorization field.", "V2")
        normalized_texts[1] = (stale, f"Archived obsolete value {previous_token} must not be used as current evidence.", "V1")
    elif stratum == "DYNAMIC_UPDATE_FRESHNESS":
        normalized_texts[0] = (current, f"Live registry V1: Orion-{task_index:02d} authorization value is {previous_token}.", "V1")

    normalized = tuple(
        ContextDocument(source_id=sid, text=text, version=version, location=f"doc-{idx + 1}", modality="text")
        for idx, (sid, text, version) in enumerate(normalized_texts)
    )

    raw_docs: list[ContextDocument] = []
    for idx, doc in enumerate(normalized):
        modality = "text"
        text = doc.text
        if stratum == "TABLE_STRUCTURED" and idx == 0:
            modality = "table"
            text = f"| unit | value | status |\n| Orion-{task_index:02d} | {token} | current |"
        elif stratum == "LONG_LAYOUT_PDF" and idx == 0:
            modality = "pdf-layout"
            text = "PDF-LAYOUT\n" + doc.text
        elif stratum == "SCANNED_MULTIMODAL" and idx == 0:
            modality = "image"
            text = f"IMAGE-TEXT-LAYER-ABSENT\nFORM ORION {task_index:02d}\nAUTH {token}"
        raw_docs.append(
            ContextDocument(
                source_id=doc.source_id,
                text=text,
                version=doc.version,
                location=doc.location,
                modality=modality,
                metadata={"artifact_name": f"artifact-{stable_hash([seed, task_index, idx])[:10]}"},
            )
        )

    if not answerable:
        required = ()
        versions: dict[str, str] = {}
    elif stratum in {"CROSS_DOC_MULTI_HOP", "RELATIONAL_GLOBAL"}:
        required = (current, ids[2])
        versions = {current: "V2", ids[2]: "V2"}
    elif stratum == "DYNAMIC_UPDATE_FRESHNESS":
        required = (current,)
        versions = {current: "V1"}
    else:
        required = (current,)
        versions = {current: "V2"}

    revision = None
    if stratum == "DYNAMIC_UPDATE_FRESHNESS":
        revision = {
            "source_id": current,
            "from_version": "V1",
            "to_version": "V2",
            "from_answer": previous_token,
            "to_answer": token,
            "replacement_text": f"Live registry V2: Orion-{task_index:02d} authorization value is {token}.",
        }

    return tuple(raw_docs), normalized, required, versions, revision


def build_context_corpus(seed: int = 20261001) -> ContextCorpus:
    rng = random.Random(seed)
    tasks: list[ContextTask] = []
    for stratum_index, stratum in enumerate(STRATA):
        for local_index in range(12):
            global_index = stratum_index * 12 + local_index
            token = f"{rng.randrange(1000, 9999)}-{rng.choice('ABCDEFGH')}{rng.randrange(10, 99)}"
            previous = f"{rng.randrange(1000, 9999)}-{rng.choice('JKLMNPQR')}{rng.randrange(10, 99)}"
            answerable = not (stratum == "CONTRADICTION_VERSION_NO_ANSWER" and local_index % 3 == 2)
            raw, normalized, required, versions, revision = _make_documents(
                seed=seed,
                stratum_index=stratum_index,
                task_index=global_index,
                token=token,
                previous_token=previous,
                answerable=answerable,
                stratum=stratum,
            )
            if not answerable:
                expected = None
                question = f"What is the current authorization value for unit Orion-{global_index:02d}? Abstain if current evidence is absent."
            elif stratum == "DYNAMIC_UPDATE_FRESHNESS":
                expected = previous
                question = f"What authorization value is currently recorded for unit Orion-{global_index:02d}?"
            else:
                expected = token
                question = f"What is the current authorization value for unit Orion-{global_index:02d}?"
            tasks.append(
                ContextTask(
                    task_id=_task_id(seed, stratum_index, local_index),
                    stratum=stratum,
                    split=_split(local_index),
                    question=question,
                    expected_answer=expected,
                    required_source_ids=required,
                    raw_documents=raw,
                    normalized_documents=normalized,
                    answerable=answerable,
                    required_versions=versions,
                    freshness_revision=revision,
                )
            )

    payload = [task.to_dict(include_sealed=True) for task in tasks]
    corpus_hash = stable_hash({"seed": seed, "tasks": payload})
    return ContextCorpus(seed=seed, tasks=tuple(tasks), corpus_hash=corpus_hash)
