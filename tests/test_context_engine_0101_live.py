from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from alien_lab.computational_atlas_providers import FakeProvider
from alien_lab.context_engine_adapters import FixtureContextAdapter
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_live import (
    Live0101Config,
    answer_with_provider,
    build_answer_prompt,
    materialize_corpus,
    select_best_standalone,
    validate_candidate_identities,
)
from alien_lab.context_engine_types import ADVANCED_PINS, ADVANCED_SYSTEMS, EvidenceBundle, EvidenceItem


class ContextEngine0101LiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = build_context_corpus(seed=20261001)

    def test_pretransfer_materialization_is_global_haystack_and_excludes_transfer_content(self) -> None:
        transfer_ids = {
            doc.source_id
            for task in self.corpus.tasks
            if task.split == "VELMA_TRANSFER"
            for doc in task.raw_documents
        }
        with tempfile.TemporaryDirectory() as tmp:
            manifest = materialize_corpus(self.corpus, Path(tmp), include_transfer=False)
            self.assertEqual(manifest["document_count"], 288)
            self.assertTrue(transfer_ids.isdisjoint(set(manifest["source_ids"])))
            self.assertEqual(len(list((Path(tmp) / "raw").iterdir())), 288)
            self.assertEqual(len(list((Path(tmp) / "normalized").iterdir())), 288)
            extensions = {path.suffix.lower() for path in (Path(tmp) / "raw").iterdir()}
            self.assertTrue({".txt", ".csv", ".png", ".pdf"}.issubset(extensions))

    def test_full_materialization_adds_exactly_96_transfer_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = materialize_corpus(self.corpus, Path(tmp), include_transfer=True)
            self.assertEqual(manifest["document_count"], 384)
            self.assertEqual(len(manifest["source_ids"]), 384)

    def test_common_answer_prompt_contains_only_question_and_delivered_evidence_contract(self) -> None:
        task = next(task for task in self.corpus.tasks if task.answerable)
        bundle = EvidenceBundle(
            task_id=task.task_id,
            system_id="TEST",
            corpus_identity=self.corpus.corpus_hash,
            plane="normalized",
            items=(EvidenceItem(source_id=task.required_source_ids[0], text="Delivered evidence text.", rank=1),),
            trace={}, query_metrics={},
        )
        prompt = build_answer_prompt(task, bundle)
        self.assertIn(task.question, prompt)
        self.assertIn("Delivered evidence text.", prompt)
        self.assertIn(task.required_source_ids[0], prompt)
        for forbidden in ("required_source_ids", "required_versions", "expected_answer", "freshness_revision", task.split, task.stratum):
            self.assertNotIn(forbidden, prompt)

    def test_answer_provider_gets_one_structured_call_with_512_output_tokens(self) -> None:
        task = next(task for task in self.corpus.tasks if task.answerable)
        bundle = EvidenceBundle(task.task_id, "TEST", self.corpus.corpus_hash, "normalized", (), {}, {})
        provider = FakeProvider("fake-qwen", [{"answer": None, "citations": [], "abstain": True}])
        result = answer_with_provider(task, bundle, provider)
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["answer_payload"]["abstain"], True)
        self.assertEqual(result["evidence_kind"], "FAKE_MECHANICS_ONLY")

    def test_live_config_requires_all_seven_external_retrieval_adapters_and_frozen_pins(self) -> None:
        payload = {
            "answer_model": {"model_id": "qwen3.5:9b-q8_0", "endpoint": "http://127.0.0.1:11434", "context_limit": 25600},
            "retrieval_adapters": {
                **{system_id: {"command": ["python", "bridge.py", system_id], "pin": pin} for system_id, pin in ADVANCED_PINS.items()},
                "DENSE_VECTOR_RAG": {"command": ["python", "dense_bridge.py"], "pin": "sealed-at-live-start"},
            },
            "velma_adapter": {"command": ["python", "velma_bridge.py"], "pin": "sealed-at-live-start"},
        }
        config = Live0101Config.from_dict(payload)
        self.assertEqual(config.answer_model.context_limit, 25600)
        self.assertEqual(set(ADVANCED_SYSTEMS), set(config.advanced_adapter_specs))
        self.assertIn("DENSE_VECTOR_RAG", config.retrieval_adapter_specs)
        bad = json.loads(json.dumps(payload))
        del bad["retrieval_adapters"]["HIPPORAG_PPR"]
        with self.assertRaises(ValueError):
            Live0101Config.from_dict(bad)
        bad_pin = json.loads(json.dumps(payload))
        bad_pin["retrieval_adapters"]["RAGFLOW_FULL"]["pin"] = "wrong"
        with self.assertRaises(ValueError):
            Live0101Config.from_dict(bad_pin)

    def test_candidate_identity_validation_fails_closed_on_wrong_pin_or_live_flag(self) -> None:
        adapters = {system: FixtureContextAdapter(system_id=system) for system in ADVANCED_SYSTEMS}
        with self.assertRaises(ValueError):
            validate_candidate_identities(adapters, required_pins=ADVANCED_PINS, allow_fixture=False)
        observed = {system: {"system_id": system, "pin": ADVANCED_PINS[system], "live": True} for system in ADVANCED_SYSTEMS}
        self.assertEqual(validate_candidate_identities(observed, required_pins=ADVANCED_PINS, allow_fixture=False)["validated"], 6)
        observed["RAGFLOW_FULL"]["pin"] = "wrong"
        with self.assertRaises(ValueError):
            validate_candidate_identities(observed, required_pins=ADVANCED_PINS, allow_fixture=False)

    def test_best_standalone_selection_uses_only_pretransfer_scored_rows(self) -> None:
        rows = [
            {"split": "DISCOVERY", "arm": "RAGFLOW_FULL", "score": 1, "silent_wrong": False, "cost": 2.0},
            {"split": "CONFIRMATORY", "arm": "RAGFLOW_FULL", "score": 0, "silent_wrong": False, "cost": 2.0},
            {"split": "DISCOVERY", "arm": "PAGEINDEX_TREE", "score": 1, "silent_wrong": False, "cost": 5.0},
            {"split": "CONFIRMATORY", "arm": "PAGEINDEX_TREE", "score": 1, "silent_wrong": False, "cost": 5.0},
        ]
        self.assertEqual(select_best_standalone(rows), "PAGEINDEX_TREE")
        poisoned = rows + [{"split": "VELMA_TRANSFER", "arm": "RAGFLOW_FULL", "score": 1, "silent_wrong": False, "cost": 0.0}]
        with self.assertRaises(ValueError):
            select_best_standalone(poisoned)


if __name__ == "__main__":
    unittest.main()
