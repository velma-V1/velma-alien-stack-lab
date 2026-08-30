from __future__ import annotations

import unittest

from alien_lab.context_engine_types import (
    ADVANCED_SYSTEMS,
    ANSWER_CONTEXT_UTF8_BYTES,
    RETRIEVAL_ARMS,
    STANDALONE_ARMS,
    STRATA,
)
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_experiment import (
    build_stage_a_ledger,
    build_stage_b_ledger,
    build_stage_c1_ledger,
    build_stage_d_ledger,
)


class ContextEngine0101ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = build_context_corpus(seed=20261001)

    def test_frozen_arm_and_budget_contract(self) -> None:
        self.assertEqual(ANSWER_CONTEXT_UTF8_BYTES, 16384)
        self.assertEqual(
            ADVANCED_SYSTEMS,
            (
                "RAGFLOW_FULL",
                "PAGEINDEX_TREE",
                "MICROSOFT_GRAPHRAG",
                "COLBERT_LATE_INTERACTION",
                "HIPPORAG_PPR",
                "SERVIETTE_LIVE_RAG",
            ),
        )
        self.assertEqual(len(RETRIEVAL_ARMS), 9)
        self.assertEqual(len(STANDALONE_ARMS), 11)
        self.assertEqual(
            STRATA,
            (
                "SINGLE_HOP_TEXT",
                "TABLE_STRUCTURED",
                "LONG_LAYOUT_PDF",
                "SCANNED_MULTIMODAL",
                "CROSS_DOC_MULTI_HOP",
                "RELATIONAL_GLOBAL",
                "CONTRADICTION_VERSION_NO_ANSWER",
                "DYNAMIC_UPDATE_FRESHNESS",
            ),
        )

    def test_corpus_is_exactly_96_balanced_tasks(self) -> None:
        self.assertEqual(len(self.corpus.tasks), 96)
        for stratum in STRATA:
            self.assertEqual(sum(task.stratum == stratum for task in self.corpus.tasks), 12)
        self.assertEqual(sum(task.split == "DISCOVERY" for task in self.corpus.tasks), 48)
        self.assertEqual(sum(task.split == "CONFIRMATORY" for task in self.corpus.tasks), 24)
        self.assertEqual(sum(task.split == "VELMA_TRANSFER" for task in self.corpus.tasks), 24)

    def test_corpus_and_task_ids_are_deterministic(self) -> None:
        replay = build_context_corpus(seed=20261001)
        different = build_context_corpus(seed=20261002)
        self.assertEqual(self.corpus.corpus_hash, replay.corpus_hash)
        self.assertEqual([t.task_id for t in self.corpus.tasks], [t.task_id for t in replay.tasks])
        self.assertNotEqual(self.corpus.corpus_hash, different.corpus_hash)

    def test_exposed_source_ids_do_not_leak_scientific_labels(self) -> None:
        forbidden = {
            "discovery",
            "confirmatory",
            "velma_transfer",
            "single_hop",
            "table_structured",
            "long_layout",
            "scanned_multimodal",
            "cross_doc",
            "relational_global",
            "contradiction",
            "dynamic_update",
            "required",
            "relevant",
            "answer",
            "oracle",
            "ragflow",
            "pageindex",
            "graphrag",
            "colbert",
            "hipporag",
            "serviette",
        }
        for task in self.corpus.tasks:
            self.assertTrue(task.raw_documents)
            self.assertTrue(task.normalized_documents)
            raw_ids = {doc.source_id for doc in task.raw_documents}
            normalized_ids = {doc.source_id for doc in task.normalized_documents}
            self.assertEqual(raw_ids, normalized_ids)
            self.assertTrue(set(task.required_source_ids).issubset(raw_ids))
            for source_id in raw_ids:
                lowered = source_id.lower()
                self.assertFalse(any(token in lowered for token in forbidden), source_id)

    def test_frozen_ledger_counts_and_split_isolation(self) -> None:
        stage_a = build_stage_a_ledger(self.corpus)
        stage_b = build_stage_b_ledger(self.corpus)
        stage_c = build_stage_c1_ledger(self.corpus, topology_ids=("T1", "T2", "T3", "T4", "T5", "T6"))
        stage_d = build_stage_d_ledger(self.corpus, standalone_id="RAGFLOW_FULL", composition_id="T1")
        self.assertEqual(len(stage_a), 792)
        self.assertEqual(len(stage_b), 648)
        self.assertEqual(len(stage_c), 144)
        self.assertEqual(len(stage_d), 120)
        task_by_id = {task.task_id: task for task in self.corpus.tasks}
        self.assertFalse(any(task_by_id[cell.task_id].split == "VELMA_TRANSFER" for cell in stage_a))
        self.assertFalse(any(task_by_id[cell.task_id].split == "VELMA_TRANSFER" for cell in stage_b))
        self.assertTrue(all(task_by_id[cell.task_id].split == "CONFIRMATORY" for cell in stage_c))
        self.assertTrue(all(task_by_id[cell.task_id].split == "VELMA_TRANSFER" for cell in stage_d))

    def test_stage_c_requires_six_unique_topologies(self) -> None:
        with self.assertRaises(ValueError):
            build_stage_c1_ledger(self.corpus, topology_ids=("T1", "T2"))
        with self.assertRaises(ValueError):
            build_stage_c1_ledger(self.corpus, topology_ids=("T1", "T1", "T2", "T3", "T4", "T5"))


if __name__ == "__main__":
    unittest.main()
