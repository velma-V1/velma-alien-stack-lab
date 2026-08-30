from __future__ import annotations

from dataclasses import replace
from statistics import mean
from typing import Any, Mapping

from .context_engine_fusion import Topology, cascade_filter_then_rank, consensus_fuse, enumerate_discovery_topologies, rrf_fuse
from .context_engine_scoring import budget_evidence, score_retrieval
from .context_engine_types import (
    ADVANCED_SYSTEMS,
    ANSWER_CONTEXT_UTF8_BYTES,
    ContextCorpus,
    ContextDocument,
    ContextTask,
    EvidenceBundle,
    EvidenceItem,
)


def build_oracle_bundle(task: ContextTask, *, corpus_identity: str) -> EvidenceBundle:
    if not task.answerable:
        items: tuple[EvidenceItem, ...] = ()
    else:
        by_id = {doc.source_id: doc for doc in task.normalized_documents}
        items = tuple(
            EvidenceItem(
                source_id=source_id,
                text=by_id[source_id].text,
                rank=rank,
                score=1.0,
                version=by_id[source_id].version,
                location=by_id[source_id].location,
                provenance={"oracle_context": True},
            )
            for rank, source_id in enumerate(task.required_source_ids, start=1)
        )
    return EvidenceBundle(
        task_id=task.task_id,
        system_id="ORACLE_CONTEXT",
        corpus_identity=corpus_identity,
        plane="oracle",
        items=items,
        trace={"oracle_context": True},
        query_metrics={"internal_model_calls": 0},
    )


def build_v2_task(task: ContextTask) -> ContextTask:
    revision = task.freshness_revision
    if task.stratum != "DYNAMIC_UPDATE_FRESHNESS" or not isinstance(revision, dict):
        raise ValueError("FRESHNESS_REVISION_REQUIRED")
    source_id = str(revision["source_id"])
    replacement_text = str(revision["replacement_text"])
    to_version = str(revision["to_version"])
    to_answer = str(revision["to_answer"])

    def revise(documents: tuple[ContextDocument, ...]) -> tuple[ContextDocument, ...]:
        found = False
        revised: list[ContextDocument] = []
        for doc in documents:
            if doc.source_id == source_id:
                revised.append(replace(doc, text=replacement_text, version=to_version))
                found = True
            else:
                revised.append(doc)
        if not found:
            raise ValueError("FRESHNESS_SOURCE_NOT_FOUND")
        return tuple(revised)

    return replace(
        task,
        expected_answer=to_answer,
        required_versions={source_id: to_version},
        raw_documents=revise(task.raw_documents),
        normalized_documents=revise(task.normalized_documents),
    )


def fuse_topology(topology: Topology, bundles_by_system: Mapping[str, EvidenceBundle]) -> EvidenceBundle:
    try:
        bundles = tuple(bundles_by_system[system_id] for system_id in topology.members)
    except KeyError as exc:
        raise ValueError(f"MISSING_TOPOLOGY_CONSTITUENT:{exc.args[0]}") from exc
    if topology.kind == "RRF":
        fused = rrf_fuse(bundles, k=60)
    elif topology.kind == "CONSENSUS":
        fused = consensus_fuse(bundles, k=60)
    elif topology.kind == "CASCADE":
        if len(bundles) != 2:
            raise ValueError("CASCADE_REQUIRES_TWO_CONSTITUENTS")
        fused = cascade_filter_then_rank(bundles[0], bundles[1], candidate_cap=16)
    else:
        raise ValueError(f"UNKNOWN_TOPOLOGY_KIND:{topology.kind}")
    trace = dict(fused.trace)
    trace["topology_id"] = topology.topology_id
    trace["members"] = list(topology.members)
    return EvidenceBundle(
        task_id=fused.task_id,
        system_id=f"COMPOSITION:{topology.topology_id}",
        corpus_identity=fused.corpus_identity,
        plane=fused.plane,
        items=fused.items,
        trace=trace,
        query_metrics=dict(fused.query_metrics),
    )


def _cost_from_bundles(bundles: tuple[EvidenceBundle, ...]) -> tuple[float | None, float | None]:
    latencies: list[float] = []
    costs: list[float] = []
    for bundle in bundles:
        latency = bundle.query_metrics.get("query_latency_ms")
        if isinstance(latency, (int, float)) and not isinstance(latency, bool):
            latencies.append(float(latency))
        cost = bundle.query_metrics.get("measured_cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            costs.append(float(cost))
    return (sum(latencies) if len(latencies) == len(bundles) else None, sum(costs) if len(costs) == len(bundles) else None)


def simulate_discovery_compositions(
    corpus: ContextCorpus,
    normalized_cache: Mapping[tuple[str, str], EvidenceBundle],
) -> list[dict[str, Any]]:
    topologies = enumerate_discovery_topologies(ADVANCED_SYSTEMS)
    discovery_tasks = tuple(task for task in corpus.tasks if task.split == "DISCOVERY")
    per_topology: dict[str, list[dict[str, Any]]] = {topology.topology_id: [] for topology in topologies}

    for task in discovery_tasks:
        bundles_by_system: dict[str, EvidenceBundle] = {}
        for system_id in ADVANCED_SYSTEMS:
            key = (task.task_id, system_id)
            if key not in normalized_cache:
                raise ValueError(f"DISCOVERY_CACHE_MISSING:{task.task_id}:{system_id}")
            bundles_by_system[system_id] = normalized_cache[key]
        constituent_sufficiency = {
            system_id: score_retrieval(task, budget_evidence(bundle, ANSWER_CONTEXT_UTF8_BYTES)).context_sufficient
            for system_id, bundle in bundles_by_system.items()
        }

        for topology in topologies:
            fused = budget_evidence(fuse_topology(topology, bundles_by_system), ANSWER_CONTEXT_UTF8_BYTES)
            score = score_retrieval(task, fused)
            constituent_bundles = tuple(bundles_by_system[system_id] for system_id in topology.members)
            latency, cost = _cost_from_bundles(constituent_bundles)
            complementarity = int(
                len(topology.members) == 2
                and score.context_sufficient
                and not any(constituent_sufficiency[system_id] for system_id in topology.members)
            )
            per_topology[topology.topology_id].append(
                {
                    "context_sufficient": score.context_sufficient,
                    "required_recall": score.required_recall,
                    "relevant_precision": score.relevant_precision,
                    "reciprocal_rank": score.reciprocal_rank,
                    "context_bytes": sum(len(item.text.encode("utf-8")) for item in fused.items),
                    "query_latency_ms": latency,
                    "measured_cost": cost,
                    "complementarity_win": complementarity,
                }
            )

    topology_map = {topology.topology_id: topology for topology in topologies}
    rows: list[dict[str, Any]] = []
    for topology_id in sorted(per_topology):
        values = per_topology[topology_id]
        topology = topology_map[topology_id]
        measured_latencies = [item["query_latency_ms"] for item in values if item["query_latency_ms"] is not None]
        measured_costs = [item["measured_cost"] for item in values if item["measured_cost"] is not None]
        rows.append(
            {
                "split": "DISCOVERY",
                "topology_id": topology_id,
                "kind": topology.kind,
                "members": list(topology.members),
                "context_sufficiency_rate": mean(float(item["context_sufficient"]) for item in values),
                "required_recall": mean(float(item["required_recall"]) for item in values),
                "relevant_precision": mean(float(item["relevant_precision"]) for item in values),
                "reciprocal_rank": mean(float(item["reciprocal_rank"]) for item in values),
                "context_bytes": round(mean(int(item["context_bytes"]) for item in values)),
                "query_latency_ms": mean(measured_latencies) if len(measured_latencies) == len(values) else None,
                "measured_cost": mean(measured_costs) if len(measured_costs) == len(values) else None,
                "complementarity_wins": sum(int(item["complementarity_win"]) for item in values),
            }
        )
    return rows


def select_best_composition(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise ValueError("COMPOSITION_SELECTION_REQUIRES_ROWS")
    if any(row.get("split") != "CONFIRMATORY" for row in rows):
        raise ValueError("CONFIRMATORY_ROWS_ONLY")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        topology_id = str(row.get("topology_id") or "")
        if not topology_id:
            raise ValueError("TOPOLOGY_ID_REQUIRED")
        grouped.setdefault(topology_id, []).append(row)

    def key(item: tuple[str, list[dict[str, Any]]]) -> tuple[Any, ...]:
        topology_id, values = item
        valid = [row for row in values if row.get("score") is not None]
        if not valid:
            return (-1.0, -1.0, float("-inf"), topology_id)
        success = sum(int(row.get("score") == 1) for row in valid) / len(valid)
        silent_wrong = sum(int(bool(row.get("silent_wrong"))) for row in valid) / len(valid)
        measured = [float(row["cost"]) for row in valid if row.get("cost") is not None]
        cost = mean(measured) if measured else float("inf")
        return (success, -silent_wrong, -cost, topology_id)

    return max(grouped.items(), key=key)[0]
