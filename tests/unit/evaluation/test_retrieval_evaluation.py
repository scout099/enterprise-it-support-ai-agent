"""Retrieval dataset and Recall@K metric tests."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from enterprise_it_support.evaluation.retrieval import (
    ResolvedRetrievalEvaluationCase,
    RetrievalEvaluationCase,
    evaluate_retrieval,
    load_retrieval_dataset,
    resolve_expected_documents,
)
from enterprise_it_support.knowledge.domain import (
    DocumentSourceType,
    DocumentStatus,
    DocumentSummaryView,
)
from enterprise_it_support.knowledge.retrieval import RelevancePolicy

DATASET = Path("data/evaluation/retrieval_cases.json")


@dataclass(frozen=True)
class Result:
    document_id: UUID
    document_title: str
    keyword_score: float | None = 0.2
    vector_similarity: float | None = 0.9


class FixedEvaluatorRetriever:
    async def search(self, query, top_k, filters, user_context):
        expected_id = UUID("10000000-0000-0000-0000-000000000001")
        if query == "hit at three":
            return (Result(expected_id, "Expected"),)
        if query == "hit at five":
            return (
                *tuple(Result(UUID(int=index + 2), f"Other {index}") for index in range(3)),
                Result(expected_id, "Expected"),
            )
        if query == "irrelevant neighbor":
            return (Result(UUID(int=99), "Distractor", keyword_score=None),)
        if query == "false answer":
            return (Result(UUID(int=98), "Distractor", keyword_score=0.2),)
        return ()


def test_phase_5_dataset_has_positive_queries_and_explicit_negative_cases() -> None:
    version, cases = load_retrieval_dataset(DATASET)

    assert version == "phase-5-v1"
    assert len(cases) == 18
    assert len({case.id for case in cases}) == 18
    assert {case.id.split("-", maxsplit=1)[0] for case in cases} == {
        "vpn",
        "outlook",
        "account",
        "negative",
    }
    positives = [case for case in cases if case.answerable]
    negatives = [case for case in cases if not case.answerable]
    assert len(positives) == 15
    assert len(negatives) == 3
    assert {case.expected_source_name for case in positives} == {"Retrieval Evaluation Library"}
    assert all(case.expected_source_name is None for case in negatives)


def test_evaluation_resolves_duplicate_titles_by_source_and_document_id() -> None:
    expected_id = UUID("10000000-0000-0000-0000-000000000001")
    wrong_id = UUID("20000000-0000-0000-0000-000000000002")
    now = datetime.now(UTC)
    documents = tuple(
        DocumentSummaryView(
            id=document_id,
            source_name=source,
            title="Shared title",
            source_type=DocumentSourceType.TXT,
            status=DocumentStatus.ACTIVE,
            owner="Demo",
            latest_version=1,
            created_at=now,
            updated_at=now,
        )
        for document_id, source in (
            (expected_id, "Expected source"),
            (wrong_id, "Distractor source"),
        )
    )

    resolved = resolve_expected_documents(
        (
            RetrievalEvaluationCase(
                id="case-1",
                query="query",
                answerable=True,
                expected_source_name="Expected source",
                expected_document_title="Shared title",
            ),
        ),
        documents,
    )

    assert resolved[0].expected_document_id == expected_id


@pytest.mark.asyncio
async def test_evaluation_calculates_recall_at_three_and_five() -> None:
    expected_id = UUID("10000000-0000-0000-0000-000000000001")
    cases = (
        ResolvedRetrievalEvaluationCase("case-1", "hit at three", True, expected_id),
        ResolvedRetrievalEvaluationCase("case-2", "hit at five", True, expected_id),
        ResolvedRetrievalEvaluationCase("case-3", "miss", True, expected_id),
        ResolvedRetrievalEvaluationCase("case-4", "irrelevant neighbor", False, None),
        ResolvedRetrievalEvaluationCase("case-5", "false answer", False, None),
    )

    report = await evaluate_retrieval(
        FixedEvaluatorRetriever(),
        dataset_version="test-v1",
        cases=cases,
        user_role="employee",
        relevance_policy=RelevancePolicy(
            min_keyword_score=0.05,
            min_vector_similarity=None,
        ),
    )

    assert report.total_cases == 5
    assert report.positive_cases == 3
    assert report.negative_cases == 2
    assert report.recall_at_3 == pytest.approx(1 / 3)
    assert report.recall_at_5 == pytest.approx(2 / 3)
    assert report.false_answer_rate == pytest.approx(1 / 2)
    assert report.abstention_accuracy == pytest.approx(1 / 2)
    assert report.missed_at_3 == ("case-2", "case-3")
    assert report.missed_at_5 == ("case-3",)
