from __future__ import annotations

import unittest

from alien_lab.context_engine_types import ContextDocument, ContextTask, EvidenceBundle, EvidenceItem
from alien_lab.context_engine_scoring import (
    budget_evidence,
    localize_failure,
    paired_exact_sign_test,
    score_retrieval,
    verify_answer,
)


def _task(*, answerable: bool = True, version: str = "V2") -> ContextTask:
    docs = (
        ContextDocument(source_id="src-a", text="Project Lark authorization code is 7139.", version=version),
        ContextDocument(source_id="src-b", text="Project Lark authorization code is 1184.", version="V1"),
        ContextDocument(source_id="src-c", text="Irrelevant maintenance note.", version="V2"),
    )
    return ContextTask(
        task_id="task-x",
        stratum="CONTRADICTION_VERSION_NO_ANSWER",
        split="DISCOVERY",
        question="What is the current Project Lark authorization code?",
        expected_answer="7139" if answerable else None,
        required_source_ids=("src-a",) if answerable else (),
        raw_documents=docs,
        normalized_documents=docs,
        answerable=answerable,
        required_versions={"src-a": version} if answerable else {},
        freshness_revision=None,
    )


def _bundle(items: tuple[EvidenceItem, ...]) -> EvidenceBundle:
    return EvidenceBundle(
        task_id="task-x",
        system_id="SYS",
        corpus_identity="corpus",
        plane="normalized",
        items=items,
        trace={},
        query_metrics={},
    )


class ContextEngine0101ScoringTests(unittest.TestCase):
    def test_budget_is_deterministic_and_never_exceeds_utf8_byte_limit(self) -> None:
        items = tuple(
            EvidenceItem(source_id=f"s{i}", text=("évidence " * 900), rank=i + 1)
            for i in range(4)
        )
        bundle = _bundle(items)
        a = budget_evidence(bundle, max_utf8_bytes=16384)
        b = budget_evidence(bundle, max_utf8_bytes=16384)
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertLessEqual(sum(len(item.text.encode("utf-8")) for item in a.items), 16384)
        self.assertEqual([item.rank for item in a.items], sorted(item.rank for item in a.items))
        for item in a.items:
            item.text.encode("utf-8").decode("utf-8")

    def test_retrieval_metrics_distinguish_required_irrelevant_and_stale(self) -> None:
        task = _task()
        result = score_retrieval(
            task,
            _bundle(
                (
                    EvidenceItem(source_id="src-b", text="old", rank=1, version="V1"),
                    EvidenceItem(source_id="src-a", text="current", rank=2, version="V2"),
                    EvidenceItem(source_id="src-c", text="noise", rank=3, version="V2"),
                )
            ),
        )
        self.assertEqual(result.required_recall, 1.0)
        self.assertAlmostEqual(result.relevant_precision, 1 / 3)
        self.assertEqual(result.first_relevant_rank, 2)
        self.assertEqual(result.reciprocal_rank, 0.5)
        self.assertTrue(result.context_sufficient)
        self.assertTrue(result.stale_selected)
        self.assertEqual(result.wrong_version_count, 1)

    def test_no_answer_task_penalizes_evidence_contamination(self) -> None:
        task = _task(answerable=False)
        clean = score_retrieval(task, _bundle(()))
        contaminated = score_retrieval(task, _bundle((EvidenceItem(source_id="src-c", text="noise", rank=1),)))
        self.assertTrue(clean.context_sufficient)
        self.assertEqual(clean.no_answer_contamination, 0)
        self.assertFalse(contaminated.context_sufficient)
        self.assertEqual(contaminated.no_answer_contamination, 1)

    def test_answer_verifier_detects_success_abstention_and_silent_wrong(self) -> None:
        task = _task()
        bundle = _bundle((EvidenceItem(source_id="src-a", text="current", rank=1, version="V2"),))
        good = verify_answer(task, {"answer": "7139", "citations": ["src-a"], "abstain": False}, bundle)
        bad = verify_answer(task, {"answer": "1184", "citations": ["src-b"], "abstain": False}, bundle)
        abstain = verify_answer(task, {"answer": None, "citations": [], "abstain": True}, bundle)
        self.assertEqual(good.score, 1)
        self.assertTrue(good.citation_correct)
        self.assertEqual(bad.score, 0)
        self.assertTrue(bad.silent_wrong)
        self.assertEqual(abstain.score, 0)
        self.assertTrue(abstain.unnecessary_abstention)

    def test_correct_abstention_on_no_answer_task_scores_success(self) -> None:
        task = _task(answerable=False)
        result = verify_answer(task, {"answer": None, "citations": [], "abstain": True}, _bundle(()))
        self.assertEqual(result.score, 1)
        self.assertTrue(result.correct_abstention)

    def test_failure_localization_separates_retrieval_truncation_reasoning_and_freshness(self) -> None:
        task = _task()
        missing = score_retrieval(task, _bundle(()))
        sufficient_bundle = _bundle((EvidenceItem(source_id="src-a", text="current", rank=1, version="V2"),))
        sufficient = score_retrieval(task, sufficient_bundle)
        wrong = verify_answer(task, {"answer": "1184", "citations": ["src-b"], "abstain": False}, sufficient_bundle)
        self.assertEqual(localize_failure(task, missing, None), "RETRIEVAL")
        self.assertEqual(localize_failure(task, sufficient, wrong), "POST_RETRIEVAL_REASONING")

        truncated = score_retrieval(task, _bundle((EvidenceItem(source_id="src-c", text="noise", rank=1),)))
        self.assertEqual(localize_failure(task, truncated, None, prebudget_sufficient=True), "CONTEXT_TRUNCATION")
        self.assertEqual(localize_failure(task, sufficient, wrong, freshness_stale=True), "FRESHNESS")

    def test_exact_sign_test_is_symmetric_and_ignores_ties(self) -> None:
        self.assertEqual(paired_exact_sign_test(0, 0), 1.0)
        self.assertAlmostEqual(paired_exact_sign_test(5, 1), paired_exact_sign_test(1, 5))
        self.assertLess(paired_exact_sign_test(10, 0), 0.01)


if __name__ == "__main__":
    unittest.main()
