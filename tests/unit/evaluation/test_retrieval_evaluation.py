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

DATASET = Path("data/evaluation/retrieval_cases.json")


@dataclass(frozen=True)
class Result:
    document_id: UUID
    document_title: str


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
        return ()


def test_phase_4_dataset_has_fifteen_unique_vpn_outlook_and_account_queries() -> None:
    version, cases = load_retrieval_dataset(DATASET)

    assert version == "phase-4-v2"
    assert len(cases) == 15
    assert len({case.id for case in cases}) == 15
    assert {case.id.split("-", maxsplit=1)[0] for case in cases} == {
        "vpn",
        "outlook",
        "account",
    }
    assert {case.expected_source_name for case in cases} == {"Retrieval Evaluation Library"}


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
        (RetrievalEvaluationCase("case-1", "query", "Expected source", "Shared title"),),
        documents,
    )

    assert resolved[0].expected_document_id == expected_id


@pytest.mark.asyncio
async def test_evaluation_calculates_recall_at_three_and_five() -> None:
    expected_id = UUID("10000000-0000-0000-0000-000000000001")
    cases = (
        ResolvedRetrievalEvaluationCase("case-1", "hit at three", expected_id),
        ResolvedRetrievalEvaluationCase("case-2", "hit at five", expected_id),
        ResolvedRetrievalEvaluationCase("case-3", "miss", expected_id),
    )

    report = await evaluate_retrieval(
        FixedEvaluatorRetriever(),
        dataset_version="test-v1",
        cases=cases,
        user_role="employee",
    )

    assert report.total_cases == 3
    assert report.recall_at_3 == pytest.approx(1 / 3)
    assert report.recall_at_5 == pytest.approx(2 / 3)
    assert report.missed_at_3 == ("case-2", "case-3")
    assert report.missed_at_5 == ("case-3",)
