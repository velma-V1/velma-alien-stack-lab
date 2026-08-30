from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from alien_lab.context_engine_adapters import FixtureContextAdapter, serialize_retrieve_request
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_experiment import (
    build_stage_a_ledger,
    build_stage_b_ledger,
    build_stage_c1_ledger,
    build_stage_d_ledger,
    run_fixture_experiment,
    validate_live_execution_gate,
)
from alien_lab.context_engine_fusion import select_six_topologies
from alien_lab.context_engine_scoring import budget_evidence
from alien_lab.context_engine_types import EvidenceBundle, EvidenceItem


class ContextEngine0101SelfAttackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = build_context_corpus(seed=20261001)
        self.by_id = {task.task_id: task for task in self.corpus.tasks}

    def test_transfer_tasks_are_cryptographically_separated_from_pretransfer_ledgers(self) -> None:
        a = build_stage_a_ledger(self.corpus)
        b = build_stage_b_ledger(self.corpus)
        c = build_stage_c1_ledger(self.corpus, topology_ids=("1", "2", "3", "4", "5", "6"))
        d = build_stage_d_ledger(self.corpus, standalone_id="RAGFLOW_FULL", composition_id="1")
        pretransfer_ids = {cell.task_id for cell in (*a, *b, *c)}
        transfer_ids = {cell.task_id for cell in d}
        self.assertTrue(transfer_ids)
        self.assertTrue(pretransfer_ids.isdisjoint(transfer_ids))

    def test_discovery_selector_refuses_non_discovery_rows(self) -> None:
        with self.assertRaises(ValueError):
            select_six_topologies([{"split": "VELMA_TRANSFER", "topology_id": "x"}])

    def test_candidate_wire_request_cannot_expose_sealed_scientific_fields(self) -> None:
        task = next(task for task in self.corpus.tasks if task.answerable)
        request = serialize_retrieve_request(task, plane="raw", max_candidates=32)
        forbidden = {"expected_answer", "required_source_ids", "required_versions", "freshness_revision"}
        self.assertTrue(forbidden.isdisjoint(request))

    def test_budget_cannot_be_bypassed_by_more_items(self) -> None:
        bundle = EvidenceBundle(
            task_id="t", system_id="s", corpus_identity="c", plane="raw",
            items=tuple(EvidenceItem(source_id=f"s{i}", text="x" * 10000, rank=i + 1) for i in range(20)),
            trace={}, query_metrics={},
        )
        delivered = budget_evidence(bundle, max_utf8_bytes=16384)
        self.assertLessEqual(sum(len(i.text.encode("utf-8")) for i in delivered.items), 16384)

    def test_fixture_adapter_never_claims_live_model_evidence(self) -> None:
        adapter = FixtureContextAdapter(system_id="PAGEINDEX_TREE")
        self.assertEqual(adapter.identity()["evidence_kind"], "FAKE_MECHANICS_ONLY")
        self.assertNotEqual(adapter.identity()["evidence_kind"], "LIVE_MODEL_EVIDENCE")

    def test_live_profile_refuses_without_parent_unlock(self) -> None:
        with self.assertRaises(ValueError):
            validate_live_execution_gate(parent_unlock_path=None)

    def test_stage_c_is_cache_only_by_interface(self) -> None:
        source = inspect.getsource(select_six_topologies)
        self.assertNotIn("adapter.retrieve", source)
        self.assertNotIn("ContextEngineAdapter", source)

    def test_stage_d_is_external_and_does_not_import_v31m4(self) -> None:
        import alien_lab.context_engine_experiment as module
        source = inspect.getsource(module)
        self.assertNotIn("import V31", source)
        self.assertNotIn("import v31", source)
        self.assertNotIn("from V31", source)
        self.assertNotIn("from v31", source)

    def test_credential_free_fixture_run_is_non_live_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = run_fixture_experiment(Path(a))
            second = run_fixture_experiment(Path(b))
            self.assertEqual(first["conclusion"], "NON_LIVE_FIXTURE_RUN")
            self.assertFalse(first["live_model_evidence"])
            self.assertEqual(first["corpus_hash"], second["corpus_hash"])
            self.assertEqual(first["fixture_fingerprint"], second["fixture_fingerprint"])
            self.assertEqual(first["stage_a_cells"], 792)
            self.assertEqual(first["stage_b_observations"], 648)
            self.assertEqual(first["stage_c1_cells"], 144)
            self.assertEqual(first["stage_d_cells"], 120)
            self.assertEqual(first["discovery_topology_count"], 156)


if __name__ == "__main__":
    unittest.main()
