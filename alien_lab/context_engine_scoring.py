from __future__ import annotations

import math
import re
from dataclasses import replace
from typing import Any

from .context_engine_types import AnswerScore, ContextTask, EvidenceBundle, EvidenceItem, RetrievalScore


def _truncate_utf8(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    return raw[:max_bytes].decode("utf-8", errors="ignore")


def budget_evidence(bundle: EvidenceBundle, max_utf8_bytes: int = 16384) -> EvidenceBundle:
    if max_utf8_bytes < 0:
        raise ValueError("CONTEXT_BUDGET_INVALID")
    remaining = max_utf8_bytes
    kept: list[EvidenceItem] = []
    for item in sorted(bundle.items, key=lambda value: (value.rank, value.source_id)):
        if remaining <= 0:
            break
        truncated = _truncate_utf8(item.text, remaining)
        if not truncated:
            break
        kept.append(replace(item, text=truncated))
        remaining -= len(truncated.encode("utf-8"))
        if truncated != item.text:
            break
    trace = dict(bundle.trace)
    trace["answer_context_utf8_bytes"] = sum(len(item.text.encode("utf-8")) for item in kept)
    trace["answer_context_budget_utf8_bytes"] = max_utf8_bytes
    return EvidenceBundle(
        task_id=bundle.task_id,
        system_id=bundle.system_id,
        corpus_identity=bundle.corpus_identity,
        plane=bundle.plane,
        items=tuple(kept),
        trace=trace,
        query_metrics=dict(bundle.query_metrics),
    )


def score_retrieval(task: ContextTask, bundle: EvidenceBundle) -> RetrievalScore:
    required = set(task.required_source_ids)
    items = tuple(sorted(bundle.items, key=lambda item: (item.rank, item.source_id)))
    ids = tuple(item.source_id for item in items)
    if not task.answerable:
        contamination = len(items)
        return RetrievalScore(
            required_recall=1.0 if not items else 0.0,
            relevant_precision=1.0 if not items else 0.0,
            first_relevant_rank=None,
            reciprocal_rank=0.0,
            context_sufficient=not items,
            wrong_version_count=0,
            stale_selected=False,
            no_answer_contamination=contamination,
            retrieved_source_ids=ids,
        )

    present_required = {item.source_id for item in items if item.source_id in required}
    recall = len(present_required) / len(required) if required else 1.0
    precision = len([item for item in items if item.source_id in required]) / len(items) if items else 0.0
    first_rank = next((item.rank for item in items if item.source_id in required), None)
    reciprocal = (1.0 / first_rank) if first_rank else 0.0

    target_versions = set(task.required_versions.values())
    wrong_version_count = 0
    for item in items:
        if item.source_id in task.required_versions:
            expected_version = task.required_versions[item.source_id]
            if item.version is not None and item.version != expected_version:
                wrong_version_count += 1
        elif item.version is not None and target_versions and item.version not in target_versions:
            wrong_version_count += 1

    version_ok = all(
        any(item.source_id == source_id and (item.version is None or item.version == version) for item in items)
        for source_id, version in task.required_versions.items()
    )
    sufficient = recall == 1.0 and version_ok
    return RetrievalScore(
        required_recall=recall,
        relevant_precision=precision,
        first_relevant_rank=first_rank,
        reciprocal_rank=reciprocal,
        context_sufficient=sufficient,
        wrong_version_count=wrong_version_count,
        stale_selected=wrong_version_count > 0,
        no_answer_contamination=0,
        retrieved_source_ids=ids,
    )


def _normalize_answer(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip()).casefold()
    return text or None


def verify_answer(task: ContextTask, answer_payload: dict[str, Any], delivered_bundle: EvidenceBundle) -> AnswerScore:
    abstain = bool(answer_payload.get("abstain", False))
    answer = _normalize_answer(answer_payload.get("answer"))
    expected = _normalize_answer(task.expected_answer)
    citations = tuple(str(item) for item in (answer_payload.get("citations") or ()))
    delivered_ids = {item.source_id for item in delivered_bundle.items}

    if not task.answerable:
        score = 1 if abstain and answer is None else 0
        return AnswerScore(
            score=score,
            citation_correct=(not citations),
            correct_abstention=bool(score),
            unnecessary_abstention=False,
            silent_wrong=bool(not abstain and score == 0),
            normalized_answer=answer,
        )

    answer_correct = bool(not abstain and answer is not None and answer == expected)
    citation_correct = bool(citations) and all(citation in delivered_ids for citation in citations) and bool(set(citations) & set(task.required_source_ids))
    score = 1 if answer_correct else 0
    return AnswerScore(
        score=score,
        citation_correct=citation_correct,
        correct_abstention=False,
        unnecessary_abstention=abstain,
        silent_wrong=bool(not abstain and score == 0),
        normalized_answer=answer,
    )


def localize_failure(
    task: ContextTask,
    retrieval_score: RetrievalScore,
    answer_score: AnswerScore | None,
    *,
    prebudget_sufficient: bool = False,
    freshness_stale: bool = False,
    normalized_counterfactual_succeeds: bool = False,
) -> str:
    if freshness_stale:
        return "FRESHNESS"
    if normalized_counterfactual_succeeds and not retrieval_score.context_sufficient:
        return "INGESTION"
    if prebudget_sufficient and not retrieval_score.context_sufficient:
        return "CONTEXT_TRUNCATION"
    if not retrieval_score.context_sufficient:
        return "RETRIEVAL"
    if answer_score is not None and answer_score.score == 0:
        if answer_score.unnecessary_abstention:
            return "ABSTENTION"
        return "POST_RETRIEVAL_REASONING"
    return "NONE"


def paired_exact_sign_test(wins: int, losses: int) -> float:
    if wins < 0 or losses < 0:
        raise ValueError("PAIRED_COUNTS_INVALID")
    n = wins + losses
    if n == 0:
        return 1.0
    tail = min(wins, losses)
    probability = sum(math.comb(n, k) for k in range(tail + 1)) / (2 ** n)
    return min(1.0, 2.0 * probability)
