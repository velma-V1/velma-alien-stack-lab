from __future__ import annotations

import json
import unittest

from alien_lab.context_engine_adapters import (
    BM25Adapter,
    FixtureContextAdapter,
    HybridRRFAdapter,
    JsonlSubprocessAdapter,
    serialize_retrieve_request,
)
from alien_lab.context_engine_types import ContextDocument, ContextTask, EvidenceBundle, EvidenceItem


def _task() -> ContextTask:
    docs = (
        ContextDocument(source_id="d1", text="amber turbine calibration token ZXQ-4917", version="V2"),
        ContextDocument(source_id="d2", text="amber turbine maintenance schedule", version="V2"),
        ContextDocument(source_id="d3", text="unrelated inventory memo", version="V2"),
    )
    return ContextTask(
        task_id="task-a",
        stratum="SINGLE_HOP_TEXT",
        split="DISCOVERY",
        question="Which record contains ZXQ-4917?",
        expected_answer="d1",
        required_source_ids=("d1",),
        raw_documents=docs,
        normalized_documents=docs,
        answerable=True,
        required_versions={"d1": "V2"},
        freshness_revision=None,
    )


class ContextEngine0101AdapterTests(unittest.TestCase):
    def test_retrieve_wire_request_never_serializes_sealed_answer_or_relevance(self) -> None:
        task = _task()
        request = serialize_retrieve_request(task, plane="normalized", max_candidates=32)
        encoded = json.dumps(request, sort_keys=True).lower()
        self.assertEqual(request["op"], "retrieve")
        self.assertIn(task.question.lower(), encoded)
        for forbidden in ("expected_answer", "required_source_ids", "required_versions", "relevance", "oracle"):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn("zxq-4917\"", encoded.split("question", 1)[0])

    def test_bm25_ranks_rare_decisive_term_first_deterministically(self) -> None:
        task = _task()
        adapter = BM25Adapter()
        adapter.index_documents(task.normalized_documents, corpus_identity="c")
        a = adapter.retrieve(task, plane="normalized")
        b = adapter.retrieve(task, plane="normalized")
        self.assertEqual(a.items[0].source_id, "d1")
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_hybrid_rrf_uses_rank_only_k60(self) -> None:
        left = EvidenceBundle(
            task_id="t", system_id="L", corpus_identity="c", plane="normalized",
            items=(EvidenceItem("a", "A", 1, score=0.01), EvidenceItem("b", "B", 2, score=9999.0)),
            trace={}, query_metrics={},
        )
        right = EvidenceBundle(
            task_id="t", system_id="R", corpus_identity="c", plane="normalized",
            items=(EvidenceItem("b", "B", 1, score=-9999.0), EvidenceItem("a", "A", 2, score=9999.0)),
            trace={}, query_metrics={},
        )
        fused = HybridRRFAdapter.fuse_rankings(left, right, k=60)
        self.assertEqual([item.source_id for item in fused.items], ["a", "b"])
        self.assertEqual(fused.trace["rrf_k"], 60)

    def test_fixture_adapter_is_explicitly_non_live(self) -> None:
        adapter = FixtureContextAdapter(system_id="RAGFLOW_FULL")
        identity = adapter.identity()
        self.assertEqual(identity["evidence_kind"], "FAKE_MECHANICS_ONLY")
        self.assertFalse(identity["live"])

    def test_subprocess_adapter_rejects_identity_mismatch(self) -> None:
        adapter = JsonlSubprocessAdapter(command=("fake-command",), sealed_identity={"system_id": "RAGFLOW_FULL", "pin": "v0.27.1"})
        with self.assertRaises(ValueError):
            adapter.validate_identity({"system_id": "RAGFLOW_FULL", "pin": "wrong"})


if __name__ == "__main__":
    unittest.main()
