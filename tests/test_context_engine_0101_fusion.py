from __future__ import annotations

import unittest

from alien_lab.context_engine_fusion import (
    cascade_filter_then_rank,
    classify_compounding,
    consensus_fuse,
    enumerate_discovery_topologies,
    rrf_fuse,
    select_six_topologies,
)
from alien_lab.context_engine_types import ADVANCED_SYSTEMS, EvidenceBundle, EvidenceItem


def _bundle(system: str, ids: tuple[str, ...]) -> EvidenceBundle:
    return EvidenceBundle(
        task_id="t",
        system_id=system,
        corpus_identity="c",
        plane="normalized",
        items=tuple(EvidenceItem(source_id=sid, text=sid, rank=i + 1) for i, sid in enumerate(ids)),
        trace={},
        query_metrics={},
    )


class ContextEngine0101FusionTests(unittest.TestCase):
    def test_topology_enumeration_is_exhaustive_for_six_advanced_systems(self) -> None:
        topologies = enumerate_discovery_topologies(ADVANCED_SYSTEMS)
        by_kind = {}
        for topology in topologies:
            by_kind[topology.kind] = by_kind.get(topology.kind, 0) + 1
        self.assertEqual(by_kind["RRF"], 63)
        self.assertEqual(by_kind["CONSENSUS"], 63)
        self.assertEqual(by_kind["CASCADE"], 30)
        self.assertEqual(len(topologies), 156)
        self.assertEqual(len({t.topology_id for t in topologies}), 156)

    def test_rrf_and_consensus_are_deterministic_without_relevance_labels(self) -> None:
        a = _bundle("A", ("x", "y", "z"))
        b = _bundle("B", ("y", "z", "x"))
        rrf = rrf_fuse((a, b), k=60)
        consensus = consensus_fuse((a, b), k=60)
        self.assertEqual(rrf.to_dict(), rrf_fuse((a, b), k=60).to_dict())
        self.assertEqual(consensus.to_dict(), consensus_fuse((a, b), k=60).to_dict())
        self.assertNotIn("relevance", str(rrf.trace).lower())
        self.assertNotIn("expected", str(consensus.trace).lower())

    def test_cascade_order_is_not_assumed_symmetric(self) -> None:
        a = _bundle("A", ("x", "y"))
        b = _bundle("B", ("z", "y", "x"))
        ab = cascade_filter_then_rank(a, b, candidate_cap=1)
        ba = cascade_filter_then_rank(b, a, candidate_cap=1)
        self.assertNotEqual([i.source_id for i in ab.items], [i.source_id for i in ba.items])

    def test_selector_uses_discovery_only_and_returns_six_unique_topologies(self) -> None:
        topologies = enumerate_discovery_topologies(ADVANCED_SYSTEMS)
        discovery_rows = []
        for idx, topology in enumerate(topologies):
            discovery_rows.append(
                {
                    "split": "DISCOVERY",
                    "topology_id": topology.topology_id,
                    "kind": topology.kind,
                    "context_sufficiency_rate": 0.5 + ((idx % 17) / 100.0),
                    "required_recall": 0.55 + ((idx % 13) / 100.0),
                    "relevant_precision": 0.60 - ((idx % 11) / 200.0),
                    "reciprocal_rank": 0.4 + ((idx % 7) / 100.0),
                    "context_bytes": 8000 + idx,
                    "query_latency_ms": 10 + idx,
                    "measured_cost": 1 + (idx % 9),
                    "complementarity_wins": idx % 5,
                }
            )
        selected = select_six_topologies(discovery_rows)
        self.assertEqual(len(selected), 6)
        self.assertEqual(len({t.topology_id for t in selected}), 6)
        self.assertEqual(
            [t.slot for t in selected],
            ["BEST_RRF", "BEST_CONSENSUS", "BEST_CASCADE", "CHEAP_PARETO", "MAX_COMPLEMENTARITY_PAIR", "FULL_ENSEMBLE_RRF"],
        )
        poisoned = discovery_rows + [{**discovery_rows[0], "split": "CONFIRMATORY", "context_sufficiency_rate": 1.0}]
        with self.assertRaises(ValueError):
            select_six_topologies(poisoned)

    def test_synergy_requires_success_over_all_constituents_and_unique_multi_source_contribution(self) -> None:
        synergistic = classify_compounding(
            composition_success=True,
            constituent_successes=(False, False),
            unique_required_contributors=("A", "B"),
            accuracy_delta=0.10,
            cost_negative=False,
        )
        fake_synergy = classify_compounding(
            composition_success=True,
            constituent_successes=(False, False),
            unique_required_contributors=("A",),
            accuracy_delta=0.10,
            cost_negative=False,
        )
        antagonistic = classify_compounding(
            composition_success=False,
            constituent_successes=(True, False),
            unique_required_contributors=(),
            accuracy_delta=-0.05,
            cost_negative=False,
        )
        self.assertEqual(synergistic, "SYNERGISTIC")
        self.assertNotEqual(fake_synergy, "SYNERGISTIC")
        self.assertEqual(antagonistic, "ANTAGONISTIC")


if __name__ == "__main__":
    unittest.main()
