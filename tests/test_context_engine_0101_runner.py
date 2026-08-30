from __future__ import annotations

import unittest

from alien_lab.context_engine_adapters import FixtureContextAdapter
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_fusion import enumerate_discovery_topologies
from alien_lab.context_engine_runner import (
    build_oracle_bundle,
    build_v2_task,
    fuse_topology,
    select_best_composition,
    simulate_discovery_compositions,
)
from alien_lab.context_engine_scoring import score_retrieval
from alien_lab.context_engine_types import ADVANCED_SYSTEMS


class ContextEngine0101RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = build_context_corpus(seed=20261001)
        self.by_id = {task.task_id: task for task in self.corpus.tasks}

    def test_oracle_bundle_contains_exact_required_sources_and_no_noise(self) -> None:
        task = next(task for task in self.corpus.tasks if task.answerable and len(task.required_source_ids) == 2)
        bundle = build_oracle_bundle(task, corpus_identity=self.corpus.corpus_hash)
        self.assertEqual({item.source_id for item in bundle.items}, set(task.required_source_ids))
        self.assertTrue(score_retrieval(task, bundle).context_sufficient)
        no_answer = next(task for task in self.corpus.tasks if not task.answerable)
        self.assertEqual(build_oracle_bundle(no_answer, corpus_identity=self.corpus.corpus_hash).items, ())

    def test_v2_task_is_separate_and_does_not_mutate_v1(self) -> None:
        task = next(task for task in self.corpus.tasks if task.stratum == "DYNAMIC_UPDATE_FRESHNESS")
        original_answer = task.expected_answer
        v2 = build_v2_task(task)
        self.assertNotEqual(v2.expected_answer, original_answer)
        self.assertEqual(task.expected_answer, original_answer)
        self.assertEqual(tuple(v2.required_versions.values()), ("V2",))
        self.assertEqual(v2.task_id, task.task_id)

    def test_discovery_composition_simulator_evaluates_all_156_topologies_without_answer_calls(self) -> None:
        cache = {}
        for task in self.corpus.tasks:
            if task.split != "DISCOVERY":
                continue
            for system_id in ADVANCED_SYSTEMS:
                cache[(task.task_id, system_id)] = FixtureContextAdapter(system_id=system_id).retrieve(task, plane="normalized")
        rows = simulate_discovery_compositions(self.corpus, cache)
        self.assertEqual(len(rows), 156)
        self.assertEqual({row["topology_id"] for row in rows}, {t.topology_id for t in enumerate_discovery_topologies(ADVANCED_SYSTEMS)})
        self.assertTrue(all(row["split"] == "DISCOVERY" for row in rows))

    def test_fuse_topology_respects_ordered_cascade(self) -> None:
        task = next(task for task in self.corpus.tasks if task.split == "DISCOVERY" and task.answerable)
        bundles = {system: FixtureContextAdapter(system_id=system).retrieve(task, plane="normalized") for system in ADVANCED_SYSTEMS}
        topologies = enumerate_discovery_topologies(ADVANCED_SYSTEMS)
        ab = next(t for t in topologies if t.topology_id == f"CASCADE[{ADVANCED_SYSTEMS[0]}->{ADVANCED_SYSTEMS[1]}]")
        ba = next(t for t in topologies if t.topology_id == f"CASCADE[{ADVANCED_SYSTEMS[1]}->{ADVANCED_SYSTEMS[0]}]")
        self.assertNotEqual(ab.topology_id, ba.topology_id)
        self.assertEqual(fuse_topology(ab, bundles).trace["first"], ADVANCED_SYSTEMS[0])
        self.assertEqual(fuse_topology(ba, bundles).trace["first"], ADVANCED_SYSTEMS[1])

    def test_best_composition_selection_uses_confirmatory_only(self) -> None:
        rows = [
            {"split": "CONFIRMATORY", "topology_id": "T1", "score": 1, "silent_wrong": False, "cost": 4.0},
            {"split": "CONFIRMATORY", "topology_id": "T1", "score": 0, "silent_wrong": False, "cost": 4.0},
            {"split": "CONFIRMATORY", "topology_id": "T2", "score": 1, "silent_wrong": False, "cost": 8.0},
            {"split": "CONFIRMATORY", "topology_id": "T2", "score": 1, "silent_wrong": False, "cost": 8.0},
        ]
        self.assertEqual(select_best_composition(rows), "T2")
        with self.assertRaises(ValueError):
            select_best_composition(rows + [{"split": "VELMA_TRANSFER", "topology_id": "T1", "score": 1}])


if __name__ == "__main__":
    unittest.main()
