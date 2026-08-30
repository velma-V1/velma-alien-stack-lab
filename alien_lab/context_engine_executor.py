from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .computational_atlas_live_types import ModelRequest, ModelResponse
from .computational_atlas_types import stable_hash
from .context_engine_adapters import BM25Adapter, ContextEngineAdapter, HybridRRFAdapter
from .context_engine_fusion import Topology, enumerate_discovery_topologies, select_six_topologies
from .context_engine_live import answer_with_provider, materialize_corpus, select_best_standalone
from .context_engine_runner import (
    build_oracle_bundle,
    build_v2_task,
    fuse_topology,
    select_best_composition,
    simulate_discovery_compositions,
)
from .context_engine_scoring import budget_evidence, score_retrieval, verify_answer
from .context_engine_types import (
    ADVANCED_SYSTEMS,
    ANSWER_CONTEXT_UTF8_BYTES,
    RETRIEVAL_ARMS,
    ContextCorpus,
    ContextTask,
    EvidenceBundle,
    EvidenceItem,
)


_TOKEN_PATTERN = re.compile(r"\b\d{4}-[A-Z]\d{2}\b")
_SOURCE_BLOCK_PATTERN = re.compile(r"\[SOURCE ([^\]]+)\]\n(.*?)(?=\n\n\[SOURCE |\Z)", re.DOTALL)


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_hashed_row(path: Path, row: dict[str, Any]) -> None:
    _atomic_json(path, {"payload": row, "sha256": stable_hash(row)})


def _fixture_payload_from_evidence(question: str, evidence_items: tuple[EvidenceItem, ...]) -> dict[str, Any]:
    for item in sorted(evidence_items, key=lambda value: (value.rank, value.source_id)):
        match = _TOKEN_PATTERN.search(item.text)
        if match:
            return {"answer": match.group(0), "citations": [item.source_id], "abstain": False}
    return {"answer": None, "citations": [], "abstain": True}


class FixtureAnswerProvider:
    provider_kind = "fake"
    model_id = "fixture-answer-v1"
    endpoint = "fixture://answer"
    supports_structured_output = True
    supports_images = False
    context_limit = 25600

    def complete(self, request: ModelRequest) -> ModelResponse:
        blocks = _SOURCE_BLOCK_PATTERN.findall(request.prompt)
        items = tuple(EvidenceItem(source_id=source_id, text=text, rank=rank) for rank, (source_id, text) in enumerate(blocks, start=1))
        payload = _fixture_payload_from_evidence(request.prompt, items)
        return ModelResponse(
            ok=True,
            text=json.dumps(payload, sort_keys=True),
            parsed_json=payload,
            model_calls=1,
            prompt_tokens=None,
            output_tokens=None,
            duration_ms=0.0,
            evidence_kind="FAKE_MECHANICS_ONLY",
            raw={"fixture": True},
        )


class FixtureVelmaAnswerAdapter:
    def identity(self) -> dict[str, Any]:
        return {"system_id": "VELMA", "pin": "fixture-v1", "live": False, "evidence_kind": "FAKE_MECHANICS_ONLY"}

    def answer(self, task: ContextTask, bundle: EvidenceBundle) -> dict[str, Any]:
        return {
            "answer_payload": _fixture_payload_from_evidence(task.question, bundle.items),
            "metrics": {"fixture": True, "model_calls": 0},
            "evidence_kind": "FAKE_MECHANICS_ONLY",
        }


def _empty_bundle(task: ContextTask, *, corpus_identity: str, system_id: str = "MODEL_ONLY") -> EvidenceBundle:
    return EvidenceBundle(task.task_id, system_id, corpus_identity, "none", (), {}, {})


def _evaluate_qwen(
    task: ContextTask,
    *,
    arm: str,
    bundle: EvidenceBundle,
    provider: Any,
    stage: str,
    diagnostic: str | None = None,
) -> dict[str, Any]:
    delivered = budget_evidence(bundle, ANSWER_CONTEXT_UTF8_BYTES)
    retrieval = score_retrieval(task, delivered)
    result = answer_with_provider(task, delivered, provider)
    if not result["ok"]:
        return {
            "stage": stage,
            "diagnostic": diagnostic,
            "split": task.split,
            "task_id": task.task_id,
            "arm": arm,
            "score": None,
            "silent_wrong": False,
            "retrieval": retrieval.to_dict(),
            "answer": None,
            "model": result,
            "cost": None,
            "status": "INFRASTRUCTURE_MODEL_FAILURE",
        }
    answer_score = verify_answer(task, result["answer_payload"], delivered)
    query_cost = bundle.query_metrics.get("measured_cost")
    cost = float(query_cost) if isinstance(query_cost, (int, float)) and not isinstance(query_cost, bool) else None
    return {
        "stage": stage,
        "diagnostic": diagnostic,
        "split": task.split,
        "task_id": task.task_id,
        "arm": arm,
        "score": answer_score.score,
        "silent_wrong": answer_score.silent_wrong,
        "retrieval": retrieval.to_dict(),
        "answer": answer_score.to_dict(),
        "model": {key: result.get(key) for key in ("model_calls", "prompt_tokens", "output_tokens", "duration_ms", "evidence_kind")},
        "cost": cost,
        "status": "VALID_SUCCESS" if answer_score.score == 1 else "VALID_UNRESOLVED",
    }


def _evaluate_velma(
    task: ContextTask,
    *,
    arm: str,
    bundle: EvidenceBundle,
    velma_adapter: Any,
    stage: str,
    diagnostic: str | None = None,
) -> dict[str, Any]:
    delivered = budget_evidence(bundle, ANSWER_CONTEXT_UTF8_BYTES)
    retrieval = score_retrieval(task, delivered)
    result = velma_adapter.answer(task, delivered)
    answer_score = verify_answer(task, result["answer_payload"], delivered)
    metrics = dict(result.get("metrics") or {})
    cost_value = metrics.get("measured_cost")
    cost = float(cost_value) if isinstance(cost_value, (int, float)) and not isinstance(cost_value, bool) else None
    return {
        "stage": stage,
        "diagnostic": diagnostic,
        "split": task.split,
        "task_id": task.task_id,
        "arm": arm,
        "score": answer_score.score,
        "silent_wrong": answer_score.silent_wrong,
        "retrieval": retrieval.to_dict(),
        "answer": answer_score.to_dict(),
        "model": {"evidence_kind": result.get("evidence_kind"), **metrics},
        "cost": cost,
        "status": "VALID_SUCCESS" if answer_score.score == 1 else "VALID_UNRESOLVED",
    }


def _all_normalized_documents(corpus: ContextCorpus, *, include_transfer: bool) -> tuple[Any, ...]:
    docs = {}
    for task in corpus.tasks:
        if not include_transfer and task.split == "VELMA_TRANSFER":
            continue
        for doc in task.normalized_documents:
            docs[doc.source_id] = doc
    return tuple(docs[source_id] for source_id in sorted(docs))


def _retrieve_conventional(
    task: ContextTask,
    *,
    bm25: BM25Adapter,
    dense: ContextEngineAdapter,
    index_id: str,
) -> dict[str, EvidenceBundle]:
    bm25_bundle = bm25.retrieve(task, plane="normalized", index_id=index_id)
    dense_bundle = dense.retrieve(task, plane="normalized", index_id=index_id)
    hybrid = HybridRRFAdapter.fuse_rankings(bm25_bundle, dense_bundle, k=60)
    return {"BM25_RAG": bm25_bundle, "DENSE_VECTOR_RAG": dense_bundle, "HYBRID_RRF_RAG": hybrid}


def _topology_by_id(topology_id: str) -> Topology:
    mapping = {topology.topology_id: topology for topology in enumerate_discovery_topologies(ADVANCED_SYSTEMS)}
    if topology_id not in mapping:
        raise ValueError(f"TOPOLOGY_NOT_FOUND:{topology_id}")
    return mapping[topology_id]


def _write_revision(task_v2: ContextTask, root: Path, *, plane: str) -> tuple[str, Path, str]:
    revision = task_v2.freshness_revision
    if not isinstance(revision, dict):
        raise ValueError("FRESHNESS_REVISION_REQUIRED")
    source_id = str(revision["source_id"])
    docs = task_v2.raw_documents if plane == "raw" else task_v2.normalized_documents
    doc = next((item for item in docs if item.source_id == source_id), None)
    if doc is None:
        raise ValueError("FRESHNESS_SOURCE_NOT_FOUND")
    directory = root / "revisions" / task_v2.task_id / plane
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{source_id}.txt"
    path.write_text(doc.text, encoding="utf-8")
    return source_id, path, doc.version


def _original_materialized_path(materialization_root: Path, task: ContextTask, *, plane: str) -> tuple[str, Path, str]:
    revision = task.freshness_revision
    if not isinstance(revision, dict):
        raise ValueError("FRESHNESS_REVISION_REQUIRED")
    source_id = str(revision["source_id"])
    manifest = json.loads((materialization_root / "materialization.json").read_text(encoding="utf-8"))
    row = next(item for item in manifest["documents"] if item["source_id"] == source_id)
    filename = row["raw_file"] if plane == "raw" else row["normalized_file"]
    return source_id, materialization_root / plane / filename, str(row["version"])


def _advanced_retrieve(
    task: ContextTask,
    adapters: Mapping[str, ContextEngineAdapter],
    *,
    plane: str,
    index_id: str,
) -> dict[str, EvidenceBundle]:
    return {
        system_id: adapters[system_id].retrieve(task, plane=plane, index_id=index_id)
        for system_id in ADVANCED_SYSTEMS
    }


def run_pipeline_with_components(
    *,
    corpus: ContextCorpus,
    retrieval_adapters: Mapping[str, ContextEngineAdapter],
    answer_provider: Any,
    velma_adapter: Any,
    output_dir: Path,
    fixture_mode: bool,
) -> dict[str, Any]:
    required_retrievers = set(ADVANCED_SYSTEMS) | {"DENSE_VECTOR_RAG"}
    if set(retrieval_adapters) != required_retrievers:
        raise ValueError(f"RETRIEVER_SET_MISMATCH:expected={sorted(required_retrievers)}:observed={sorted(retrieval_adapters)}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pre_root = output_dir / "corpus-pretransfer"
    pre_manifest = materialize_corpus(corpus, pre_root, include_transfer=False)
    pre_tasks = tuple(task for task in corpus.tasks if task.split != "VELMA_TRANSFER")
    by_task = {task.task_id: task for task in corpus.tasks}

    advanced_raw_index = "0101-A-pretransfer-raw"
    normalized_index = "0101-B-pretransfer-normalized"

    for system_id in ADVANCED_SYSTEMS:
        retrieval_adapters[system_id].index(
            corpus_dir=str(pre_root), corpus_identity=corpus.corpus_hash, plane="raw", index_id=advanced_raw_index
        )
    dense = retrieval_adapters["DENSE_VECTOR_RAG"]
    dense.index(corpus_dir=str(pre_root), corpus_identity=corpus.corpus_hash, plane="normalized", index_id=normalized_index)
    bm25 = BM25Adapter()
    bm25.index_documents(_all_normalized_documents(corpus, include_transfer=False), corpus_identity=corpus.corpus_hash, index_id=normalized_index)

    stage_a_rows: list[dict[str, Any]] = []
    stage_a_cache: dict[tuple[str, str], EvidenceBundle] = {}
    for task in pre_tasks:
        conventional = _retrieve_conventional(task, bm25=bm25, dense=dense, index_id=normalized_index)
        advanced = _advanced_retrieve(task, retrieval_adapters, plane="raw", index_id=advanced_raw_index)
        bundles: dict[str, EvidenceBundle] = {
            "MODEL_ONLY": _empty_bundle(task, corpus_identity=corpus.corpus_hash),
            **conventional,
            **advanced,
            "ORACLE_CONTEXT": build_oracle_bundle(task, corpus_identity=corpus.corpus_hash),
        }
        for arm, bundle in bundles.items():
            stage_a_cache[(task.task_id, arm)] = bundle
            row = _evaluate_qwen(task, arm=arm, bundle=bundle, provider=answer_provider, stage="A")
            stage_a_rows.append(row)
            _write_hashed_row(output_dir / "stage-a" / f"{task.task_id}-{stable_hash(arm)[:10]}.json", row)

    for system_id in ADVANCED_SYSTEMS:
        retrieval_adapters[system_id].index(
            corpus_dir=str(pre_root), corpus_identity=corpus.corpus_hash, plane="normalized", index_id=normalized_index
        )

    stage_b_rows: list[dict[str, Any]] = []
    stage_b_cache: dict[tuple[str, str], EvidenceBundle] = {}
    for task in pre_tasks:
        conventional = {arm: stage_a_cache[(task.task_id, arm)] for arm in ("BM25_RAG", "DENSE_VECTOR_RAG", "HYBRID_RRF_RAG")}
        advanced = _advanced_retrieve(task, retrieval_adapters, plane="normalized", index_id=normalized_index)
        for arm, bundle in {**conventional, **advanced}.items():
            stage_b_cache[(task.task_id, arm)] = bundle
            delivered = budget_evidence(bundle, ANSWER_CONTEXT_UTF8_BYTES)
            retrieval = score_retrieval(task, delivered)
            row = {
                "stage": "B",
                "diagnostic": None,
                "split": task.split,
                "task_id": task.task_id,
                "arm": arm,
                "score": None,
                "retrieval": retrieval.to_dict(),
                "context_bytes": sum(len(item.text.encode("utf-8")) for item in delivered.items),
                "query_metrics": dict(bundle.query_metrics),
                "status": "RETRIEVAL_OBSERVATION",
            }
            stage_b_rows.append(row)
            _write_hashed_row(output_dir / "stage-b" / f"{task.task_id}-{stable_hash(arm)[:10]}.json", row)

    discovery_rows = simulate_discovery_compositions(corpus, stage_b_cache)
    selected = select_six_topologies(discovery_rows)
    selected_ids = tuple(item.topology_id for item in selected)
    _atomic_json(output_dir / "discovery-composition-search.json", {"rows": discovery_rows, "selected": [item.__dict__ for item in selected]})

    stage_c_rows: list[dict[str, Any]] = []
    for task in pre_tasks:
        if task.split != "CONFIRMATORY":
            continue
        advanced_bundles = {system_id: stage_b_cache[(task.task_id, system_id)] for system_id in ADVANCED_SYSTEMS}
        for topology_id in selected_ids:
            bundle = fuse_topology(_topology_by_id(topology_id), advanced_bundles)
            row = _evaluate_qwen(task, arm="COMPOSITION", bundle=bundle, provider=answer_provider, stage="C1")
            row["topology_id"] = topology_id
            stage_c_rows.append(row)
            _write_hashed_row(output_dir / "stage-c1" / f"{task.task_id}-{stable_hash(topology_id)[:12]}.json", row)

    best_standalone = select_best_standalone(stage_a_rows)
    best_composition = select_best_composition(stage_c_rows)

    dynamic_pre = tuple(task for task in pre_tasks if task.stratum == "DYNAMIC_UPDATE_FRESHNESS")
    stage_b_v2_cache: dict[tuple[str, str], EvidenceBundle] = {}
    stage_a_v2_rows: list[dict[str, Any]] = []
    stage_b_v2_rows: list[dict[str, Any]] = []
    stage_c_v2_rows: list[dict[str, Any]] = []

    for task in dynamic_pre:
        v2 = build_v2_task(task)
        source_id_raw, v2_raw_path, v2_raw_version = _write_revision(v2, output_dir, plane="raw")
        _, original_raw_path, original_raw_version = _original_materialized_path(pre_root, task, plane="raw")
        advanced_raw_v2: dict[str, EvidenceBundle] = {}
        for system_id in ADVANCED_SYSTEMS:
            adapter = retrieval_adapters[system_id]
            adapter.update(index_id=advanced_raw_index, source_id=source_id_raw, document_path=str(v2_raw_path), version=v2_raw_version)
            advanced_raw_v2[system_id] = adapter.retrieve(v2, plane="raw", index_id=advanced_raw_index)
            adapter.update(index_id=advanced_raw_index, source_id=source_id_raw, document_path=str(original_raw_path), version=original_raw_version)

        source_id_norm, v2_norm_path, v2_norm_version = _write_revision(v2, output_dir, plane="normalized")
        _, original_norm_path, original_norm_version = _original_materialized_path(pre_root, task, plane="normalized")
        bm25.update(index_id=normalized_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)
        dense.update(index_id=normalized_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)
        advanced_norm_v2: dict[str, EvidenceBundle] = {}
        for system_id in ADVANCED_SYSTEMS:
            adapter = retrieval_adapters[system_id]
            adapter.update(index_id=normalized_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)
            advanced_norm_v2[system_id] = adapter.retrieve(v2, plane="normalized", index_id=normalized_index)
        conventional_v2 = _retrieve_conventional(v2, bm25=bm25, dense=dense, index_id=normalized_index)
        for arm, bundle in {**conventional_v2, **advanced_norm_v2}.items():
            stage_b_v2_cache[(task.task_id, arm)] = bundle
            retrieval = score_retrieval(v2, budget_evidence(bundle, ANSWER_CONTEXT_UTF8_BYTES))
            row = {
                "stage": "B",
                "diagnostic": "FRESHNESS_V2",
                "split": task.split,
                "task_id": task.task_id,
                "arm": arm,
                "score": None,
                "retrieval": retrieval.to_dict(),
                "status": "RETRIEVAL_FRESHNESS_OBSERVATION",
            }
            stage_b_v2_rows.append(row)

        bm25.update(index_id=normalized_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version)
        dense.update(index_id=normalized_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version)
        for system_id in ADVANCED_SYSTEMS:
            retrieval_adapters[system_id].update(
                index_id=normalized_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version
            )

        v2_bundles = {
            "MODEL_ONLY": _empty_bundle(v2, corpus_identity=corpus.corpus_hash),
            **conventional_v2,
            **advanced_raw_v2,
            "ORACLE_CONTEXT": build_oracle_bundle(v2, corpus_identity=corpus.corpus_hash),
        }
        for arm, bundle in v2_bundles.items():
            row = _evaluate_qwen(v2, arm=arm, bundle=bundle, provider=answer_provider, stage="A", diagnostic="FRESHNESS_V2")
            stage_a_v2_rows.append(row)

        if task.split == "CONFIRMATORY":
            bundles_for_comp = {system_id: stage_b_v2_cache[(task.task_id, system_id)] for system_id in ADVANCED_SYSTEMS}
            for topology_id in selected_ids:
                bundle = fuse_topology(_topology_by_id(topology_id), bundles_for_comp)
                row = _evaluate_qwen(v2, arm="COMPOSITION", bundle=bundle, provider=answer_provider, stage="C1", diagnostic="FRESHNESS_V2")
                row["topology_id"] = topology_id
                stage_c_v2_rows.append(row)

    full_root = output_dir / "corpus-full-transfer"
    full_manifest = materialize_corpus(corpus, full_root, include_transfer=True)
    full_raw_index = "0101-D-full-raw"
    full_norm_index = "0101-D-full-normalized"
    for system_id in ADVANCED_SYSTEMS:
        retrieval_adapters[system_id].index(
            corpus_dir=str(full_root), corpus_identity=corpus.corpus_hash, plane="raw", index_id=full_raw_index
        )
        retrieval_adapters[system_id].index(
            corpus_dir=str(full_root), corpus_identity=corpus.corpus_hash, plane="normalized", index_id=full_norm_index
        )
    dense.index(corpus_dir=str(full_root), corpus_identity=corpus.corpus_hash, plane="normalized", index_id=full_norm_index)
    bm25.index_documents(_all_normalized_documents(corpus, include_transfer=True), corpus_identity=corpus.corpus_hash, index_id=full_norm_index)

    selected_topology = _topology_by_id(best_composition)
    stage_d_rows: list[dict[str, Any]] = []
    transfer_tasks = tuple(task for task in corpus.tasks if task.split == "VELMA_TRANSFER")

    def standalone_bundle(task: ContextTask) -> EvidenceBundle:
        if best_standalone == "BM25_RAG":
            return bm25.retrieve(task, plane="normalized", index_id=full_norm_index)
        if best_standalone == "DENSE_VECTOR_RAG":
            return dense.retrieve(task, plane="normalized", index_id=full_norm_index)
        if best_standalone == "HYBRID_RRF_RAG":
            return _retrieve_conventional(task, bm25=bm25, dense=dense, index_id=full_norm_index)["HYBRID_RRF_RAG"]
        return retrieval_adapters[best_standalone].retrieve(task, plane="raw", index_id=full_raw_index)

    def composition_bundle(task: ContextTask) -> EvidenceBundle:
        bundles = {
            system_id: retrieval_adapters[system_id].retrieve(task, plane="normalized", index_id=full_norm_index)
            for system_id in selected_topology.members
        }
        return fuse_topology(selected_topology, bundles)

    for task in transfer_tasks:
        standalone = standalone_bundle(task)
        composition = composition_bundle(task)
        rows = (
            _evaluate_qwen(task, arm="QWEN_NO_CONTEXT", bundle=_empty_bundle(task, corpus_identity=corpus.corpus_hash), provider=answer_provider, stage="D"),
            _evaluate_qwen(task, arm="QWEN_BEST_STANDALONE_CONTEXT", bundle=standalone, provider=answer_provider, stage="D"),
            _evaluate_velma(task, arm="VELMA_BASELINE", bundle=_empty_bundle(task, corpus_identity=corpus.corpus_hash), velma_adapter=velma_adapter, stage="D"),
            _evaluate_velma(task, arm="VELMA_BEST_STANDALONE_CONTEXT", bundle=standalone, velma_adapter=velma_adapter, stage="D"),
            _evaluate_velma(task, arm="VELMA_BEST_CONFIRMED_COMPOSITION", bundle=composition, velma_adapter=velma_adapter, stage="D"),
        )
        stage_d_rows.extend(rows)

    stage_d_v2_rows: list[dict[str, Any]] = []
    for task in transfer_tasks:
        if task.stratum != "DYNAMIC_UPDATE_FRESHNESS":
            continue
        v2 = build_v2_task(task)
        source_id_raw, v2_raw_path, v2_raw_version = _write_revision(v2, output_dir, plane="raw")
        _, original_raw_path, original_raw_version = _original_materialized_path(full_root, task, plane="raw")
        source_id_norm, v2_norm_path, v2_norm_version = _write_revision(v2, output_dir, plane="normalized")
        _, original_norm_path, original_norm_version = _original_materialized_path(full_root, task, plane="normalized")

        for system_id in ADVANCED_SYSTEMS:
            retrieval_adapters[system_id].update(index_id=full_raw_index, source_id=source_id_raw, document_path=str(v2_raw_path), version=v2_raw_version)
            retrieval_adapters[system_id].update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)
        dense.update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)
        bm25.update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(v2_norm_path), version=v2_norm_version)

        standalone = standalone_bundle(v2)
        composition = composition_bundle(v2)
        stage_d_v2_rows.extend(
            (
                _evaluate_qwen(v2, arm="QWEN_NO_CONTEXT", bundle=_empty_bundle(v2, corpus_identity=corpus.corpus_hash), provider=answer_provider, stage="D", diagnostic="FRESHNESS_V2"),
                _evaluate_qwen(v2, arm="QWEN_BEST_STANDALONE_CONTEXT", bundle=standalone, provider=answer_provider, stage="D", diagnostic="FRESHNESS_V2"),
                _evaluate_velma(v2, arm="VELMA_BASELINE", bundle=_empty_bundle(v2, corpus_identity=corpus.corpus_hash), velma_adapter=velma_adapter, stage="D", diagnostic="FRESHNESS_V2"),
                _evaluate_velma(v2, arm="VELMA_BEST_STANDALONE_CONTEXT", bundle=standalone, velma_adapter=velma_adapter, stage="D", diagnostic="FRESHNESS_V2"),
                _evaluate_velma(v2, arm="VELMA_BEST_CONFIRMED_COMPOSITION", bundle=composition, velma_adapter=velma_adapter, stage="D", diagnostic="FRESHNESS_V2"),
            )
        )

        for system_id in ADVANCED_SYSTEMS:
            retrieval_adapters[system_id].update(index_id=full_raw_index, source_id=source_id_raw, document_path=str(original_raw_path), version=original_raw_version)
            retrieval_adapters[system_id].update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version)
        dense.update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version)
        bm25.update(index_id=full_norm_index, source_id=source_id_norm, document_path=str(original_norm_path), version=original_norm_version)

    selection = {
        "selected_topology_ids": list(selected_ids),
        "best_standalone_context": best_standalone,
        "best_confirmed_composition": best_composition,
    }
    _atomic_json(output_dir / "selection.json", selection)

    fingerprint_payload = {
        "corpus_hash": corpus.corpus_hash,
        "selection": selection,
        "stage_a": stage_a_rows,
        "stage_b": stage_b_rows,
        "stage_c1": stage_c_rows,
        "stage_d": stage_d_rows,
        "freshness_counts": [len(stage_a_v2_rows), len(stage_b_v2_rows), len(stage_c_v2_rows), len(stage_d_v2_rows)],
        "fixture_mode": fixture_mode,
    }
    summary = {
        "conclusion": "NON_LIVE_FIXTURE_RUN" if fixture_mode else "DISCOVERY_COMPLETE",
        "live_model_evidence": not fixture_mode,
        "stage_a_base_cells": len(stage_a_rows),
        "stage_b_base_observations": len(stage_b_rows),
        "discovery_topologies": len(discovery_rows),
        "stage_c1_base_cells": len(stage_c_rows),
        "stage_d_base_cells": len(stage_d_rows),
        "stage_a_freshness_v2_cells": len(stage_a_v2_rows),
        "stage_b_freshness_v2_observations": len(stage_b_v2_rows),
        "stage_c1_freshness_v2_cells": len(stage_c_v2_rows),
        "stage_d_freshness_v2_cells": len(stage_d_v2_rows),
        "selected_topology_ids": list(selected_ids),
        "best_standalone_context": best_standalone,
        "best_confirmed_composition": best_composition,
        "pretransfer_document_count": pre_manifest["document_count"],
        "full_document_count": full_manifest["document_count"],
        "pipeline_fingerprint": stable_hash(fingerprint_payload),
    }
    _atomic_json(output_dir / "pipeline-summary.json", summary)
    return summary
