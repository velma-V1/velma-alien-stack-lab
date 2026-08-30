from __future__ import annotations

import json
import unittest

from alien_lab.context_engine_adapters import (
    JsonlAnswerSystemAdapter,
    serialize_answer_request,
    serialize_index_request,
    serialize_retrieve_request,
    serialize_update_request,
)
from alien_lab.context_engine_corpus import build_context_corpus
from alien_lab.context_engine_types import EvidenceBundle, EvidenceItem


class ContextEngine0101ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = build_context_corpus(seed=20261001)
        self.task = next(task for task in self.corpus.tasks if task.answerable)

    def test_index_request_exposes_only_materialized_corpus_identity(self) -> None:
        request = serialize_index_request(
            corpus_dir="C:/evidence/pretransfer/raw",
            corpus_identity=self.corpus.corpus_hash,
            plane="raw",
            index_id="stage-a-pretransfer-raw",
        )
        self.assertEqual(request["op"], "index")
        encoded = json.dumps(request, sort_keys=True).lower()
        for forbidden in ("expected_answer", "required_source", "relevance", "oracle"):
            self.assertNotIn(forbidden, encoded)

    def test_retrieve_request_binds_index_without_scientific_labels(self) -> None:
        request = serialize_retrieve_request(self.task, plane="raw", max_candidates=32, index_id="stage-a-pretransfer-raw")
        self.assertEqual(request["index_id"], "stage-a-pretransfer-raw")
        encoded = json.dumps(request, sort_keys=True).lower()
        for forbidden in ("expected_answer", "required_source_ids", "required_versions", "relevance", "oracle"):
            self.assertNotIn(forbidden, encoded)

    def test_update_request_contains_source_revision_but_not_expected_answer(self) -> None:
        request = serialize_update_request(
            index_id="stage-a-pretransfer-raw",
            source_id="src-abc",
            document_path="C:/evidence/revisions/src-abc.txt",
            version="V2",
        )
        self.assertEqual(request["op"], "update")
        encoded = json.dumps(request, sort_keys=True).lower()
        self.assertIn("src-abc", encoded)
        for forbidden in ("expected_answer", "required_source", "relevance", "oracle"):
            self.assertNotIn(forbidden, encoded)

    def test_velma_answer_request_receives_only_question_and_delivered_evidence(self) -> None:
        bundle = EvidenceBundle(
            self.task.task_id,
            "RAGFLOW_FULL",
            self.corpus.corpus_hash,
            "raw",
            (EvidenceItem(self.task.required_source_ids[0], "evidence", 1),),
            {},
            {},
        )
        request = serialize_answer_request(self.task, bundle)
        self.assertEqual(request["op"], "answer")
        encoded = json.dumps(request, sort_keys=True).lower()
        self.assertIn(self.task.question.lower(), encoded)
        for forbidden in ("expected_answer", "required_source_ids", "required_versions", "freshness_revision", "relevance", "oracle"):
            self.assertNotIn(forbidden, encoded)

    def test_answer_adapter_rejects_identity_mismatch_without_starting_process(self) -> None:
        adapter = JsonlAnswerSystemAdapter(command=("fake",), sealed_identity={"system_id": "VELMA", "pin": "abc"})
        with self.assertRaises(ValueError):
            adapter.validate_identity({"system_id": "VELMA", "pin": "wrong"})


if __name__ == "__main__":
    unittest.main()
