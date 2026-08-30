from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Any, Iterable

from .context_engine_types import ADVANCED_SYSTEMS, EvidenceBundle, EvidenceItem


@dataclass(frozen=True)
class Topology:
    kind: str
    members: tuple[str, ...]
    topology_id: str


@dataclass(frozen=True)
class SelectedTopology:
    slot: str
    topology_id: str
    kind: str
    members: tuple[str, ...]


def _bundle_from_scores(
    bundles: tuple[EvidenceBundle, ...],
    *,
    system_id: str,
    scores: dict[str, float],
    counts: dict[str, int] | None = None,
    trace: dict[str, Any] | None = None,
) -> EvidenceBundle:
    if not bundles:
        raise ValueError("FUSION_REQUIRES_BUNDLE")
    exemplars: dict[str, EvidenceItem] = {}
    for bundle in bundles:
        for item in bundle.items:
            exemplars.setdefault(item.source_id, item)
    if counts is None:
        ordered = sorted(scores, key=lambda source_id: (-scores[source_id], source_id))
    else:
        ordered = sorted(scores, key=lambda source_id: (-counts.get(source_id, 0), -scores[source_id], source_id))
    items = tuple(
        EvidenceItem(
            source_id=source_id,
            text=exemplars[source_id].text,
            rank=rank,
            score=scores[source_id],
            version=exemplars[source_id].version,
            location=exemplars[source_id].location,
            provenance={"fusion": system_id, "source_systems": [bundle.system_id for bundle in bundles]},
        )
        for rank, source_id in enumerate(ordered, start=1)
    )
    return EvidenceBundle(
        task_id=bundles[0].task_id,
        system_id=system_id,
        corpus_identity=bundles[0].corpus_identity,
        plane=bundles[0].plane,
        items=items,
        trace=dict(trace or {}),
        query_metrics={},
    )


def rrf_fuse(bundles: Iterable[EvidenceBundle], *, k: int = 60) -> EvidenceBundle:
    materialized = tuple(bundles)
    scores: dict[str, float] = {}
    for bundle in materialized:
        for item in bundle.items:
            scores[item.source_id] = scores.get(item.source_id, 0.0) + 1.0 / (k + item.rank)
    return _bundle_from_scores(materialized, system_id="COMPOSITION_RRF", scores=scores, trace={"policy": "RRF", "k": k})


def consensus_fuse(bundles: Iterable[EvidenceBundle], *, k: int = 60) -> EvidenceBundle:
    materialized = tuple(bundles)
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    for bundle in materialized:
        seen: set[str] = set()
        for item in bundle.items:
            scores[item.source_id] = scores.get(item.source_id, 0.0) + 1.0 / (k + item.rank)
            if item.source_id not in seen:
                counts[item.source_id] = counts.get(item.source_id, 0) + 1
                seen.add(item.source_id)
    return _bundle_from_scores(
        materialized,
        system_id="COMPOSITION_CONSENSUS",
        scores=scores,
        counts=counts,
        trace={"policy": "CONSENSUS", "k": k},
    )


def cascade_filter_then_rank(first: EvidenceBundle, second: EvidenceBundle, *, candidate_cap: int) -> EvidenceBundle:
    if candidate_cap <= 0:
        raise ValueError("CANDIDATE_CAP_INVALID")
    allowed = {item.source_id for item in sorted(first.items, key=lambda item: (item.rank, item.source_id))[:candidate_cap]}
    retained = [item for item in sorted(second.items, key=lambda item: (item.rank, item.source_id)) if item.source_id in allowed]
    items = tuple(
        EvidenceItem(
            source_id=item.source_id,
            text=item.text,
            rank=rank,
            score=item.score,
            version=item.version,
            location=item.location,
            provenance={"cascade_first": first.system_id, "cascade_second": second.system_id},
        )
        for rank, item in enumerate(retained, start=1)
    )
    return EvidenceBundle(
        task_id=first.task_id,
        system_id=f"CASCADE:{first.system_id}->{second.system_id}",
        corpus_identity=first.corpus_identity,
        plane=first.plane,
        items=items,
        trace={"policy": "CASCADE", "first": first.system_id, "second": second.system_id, "candidate_cap": candidate_cap},
        query_metrics={},
    )


def enumerate_discovery_topologies(system_ids: tuple[str, ...] = ADVANCED_SYSTEMS) -> tuple[Topology, ...]:
    systems = tuple(system_ids)
    if len(systems) != 6 or len(set(systems)) != 6:
        raise ValueError("SIX_UNIQUE_ADVANCED_SYSTEMS_REQUIRED")
    topologies: list[Topology] = []
    for size in range(1, len(systems) + 1):
        for members in combinations(systems, size):
            label = "+".join(members)
            topologies.append(Topology("RRF", members, f"RRF[{label}]"))
            topologies.append(Topology("CONSENSUS", members, f"CONSENSUS[{label}]"))
    for first, second in permutations(systems, 2):
        topologies.append(Topology("CASCADE", (first, second), f"CASCADE[{first}->{second}]"))
    return tuple(topologies)


def _metric_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        float(row.get("context_sufficiency_rate", 0.0)),
        float(row.get("required_recall", 0.0)),
        float(row.get("relevant_precision", 0.0)),
        float(row.get("reciprocal_rank", 0.0)),
        -int(row.get("context_bytes", 10**18)),
        -float(row.get("query_latency_ms", 10**18)),
        str(row.get("topology_id", "")),
    )


def _topology_map() -> dict[str, Topology]:
    return {topology.topology_id: topology for topology in enumerate_discovery_topologies(ADVANCED_SYSTEMS)}


def _choose_best(rows: list[dict[str, Any]], *, kind: str | None = None, excluded: set[str] | None = None) -> dict[str, Any]:
    excluded = excluded or set()
    candidates = [row for row in rows if row.get("topology_id") not in excluded and (kind is None or row.get("kind") == kind)]
    if not candidates:
        raise ValueError("NO_UNIQUE_TOPOLOGY_AVAILABLE")
    return max(candidates, key=_metric_key)


def select_six_topologies(discovery_rows: list[dict[str, Any]]) -> tuple[SelectedTopology, ...]:
    if not discovery_rows or any(row.get("split") != "DISCOVERY" for row in discovery_rows):
        raise ValueError("DISCOVERY_ONLY_REQUIRED")
    topology_by_id = _topology_map()
    for row in discovery_rows:
        if row.get("topology_id") not in topology_by_id:
            raise ValueError(f"UNKNOWN_TOPOLOGY:{row.get('topology_id')}")

    used: set[str] = set()
    selected: list[SelectedTopology] = []

    def add(slot: str, row: dict[str, Any]) -> None:
        topology = topology_by_id[str(row["topology_id"])]
        selected.append(SelectedTopology(slot, topology.topology_id, topology.kind, topology.members))
        used.add(topology.topology_id)

    add("BEST_RRF", _choose_best(discovery_rows, kind="RRF", excluded=used))
    add("BEST_CONSENSUS", _choose_best(discovery_rows, kind="CONSENSUS", excluded=used))
    add("BEST_CASCADE", _choose_best(discovery_rows, kind="CASCADE", excluded=used))

    best_sufficiency = max(float(row.get("context_sufficiency_rate", 0.0)) for row in discovery_rows)
    best_recall = max(float(row.get("required_recall", 0.0)) for row in discovery_rows)
    pareto = [
        row for row in discovery_rows
        if row.get("topology_id") not in used
        and float(row.get("context_sufficiency_rate", 0.0)) >= best_sufficiency - 0.01
        and float(row.get("required_recall", 0.0)) >= best_recall - 0.02
    ]
    if pareto:
        cheap = min(
            pareto,
            key=lambda row: (
                float(row.get("measured_cost", float("inf"))),
                -float(row.get("context_sufficiency_rate", 0.0)),
                -float(row.get("required_recall", 0.0)),
                str(row.get("topology_id")),
            ),
        )
    else:
        cheap = _choose_best(discovery_rows, excluded=used)
    add("CHEAP_PARETO", cheap)

    pair_rows = [
        row for row in discovery_rows
        if row.get("topology_id") not in used
        and len(topology_by_id[str(row["topology_id"])].members) == 2
    ]
    if pair_rows:
        complement = max(pair_rows, key=lambda row: (int(row.get("complementarity_wins", 0)),) + _metric_key(row))
    else:
        complement = _choose_best(discovery_rows, excluded=used)
    add("MAX_COMPLEMENTARITY_PAIR", complement)

    full_id = "RRF[" + "+".join(ADVANCED_SYSTEMS) + "]"
    full_row = next((row for row in discovery_rows if row.get("topology_id") == full_id and full_id not in used), None)
    if full_row is None:
        full_row = _choose_best(discovery_rows, kind="RRF", excluded=used)
    add("FULL_ENSEMBLE_RRF", full_row)

    if len(selected) != 6 or len({item.topology_id for item in selected}) != 6:
        raise ValueError("SIX_UNIQUE_SELECTION_FAILED")
    return tuple(selected)


def classify_compounding(
    *,
    composition_success: bool,
    constituent_successes: tuple[bool, ...],
    unique_required_contributors: tuple[str, ...],
    accuracy_delta: float,
    cost_negative: bool,
) -> str:
    if composition_success and constituent_successes and not any(constituent_successes) and len(set(unique_required_contributors)) >= 2:
        return "SYNERGISTIC"
    if cost_negative and accuracy_delta > 0:
        return "COST_NEGATIVE"
    if accuracy_delta < 0 or (not composition_success and any(constituent_successes)):
        return "ANTAGONISTIC"
    if accuracy_delta > 0:
        return "ADDITIVE"
    if accuracy_delta == 0:
        return "REDUNDANT"
    return "INCONCLUSIVE"
