"""Deterministic retrieval and relevance-gate evaluation for grounded RAG."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from enterprise_it_support.knowledge.domain import DocumentSummaryView
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    RelevancePolicy,
    SearchFilters,
    UserContext,
)


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """One query and the stable source identity of its expected Document."""

    id: str
    query: str
    answerable: bool
    expected_source_name: str | None
    expected_document_title: str | None


@dataclass(frozen=True)
class ResolvedRetrievalEvaluationCase:
    """Evaluation case whose expected source has been resolved to a Document UUID."""

    id: str
    query: str
    answerable: bool
    expected_document_id: UUID | None


@dataclass(frozen=True)
class RetrievalCaseResult:
    """Per-query retrieval hit and whether the relevance gate would call the model."""

    id: str
    expected_answerable: bool
    would_call_model: bool
    hit_at_3: bool
    hit_at_5: bool
    retrieved_document_ids: tuple[UUID, ...]
    retrieved_document_titles: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    """Retrieval recall plus deterministic relevance-gate abstention metrics."""

    dataset_version: str
    total_cases: int
    positive_cases: int
    negative_cases: int
    recall_at_3: float
    recall_at_5: float
    false_answer_rate: float
    abstention_accuracy: float
    results: tuple[RetrievalCaseResult, ...]

    @property
    def missed_at_3(self) -> tuple[str, ...]:
        return tuple(
            result.id
            for result in self.results
            if result.expected_answerable and not result.hit_at_3
        )

    @property
    def missed_at_5(self) -> tuple[str, ...]:
        return tuple(
            result.id
            for result in self.results
            if result.expected_answerable and not result.hit_at_5
        )


def load_retrieval_dataset(
    path: Path,
) -> tuple[str, tuple[RetrievalEvaluationCase, ...]]:
    """Load a versioned JSON retrieval dataset with basic integrity checks."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = str(raw.get("version", "")).strip()
    raw_cases = raw.get("cases")
    if not version or not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Retrieval dataset must contain a version and non-empty cases")
    cases = []
    for item in raw_cases:
        answerable = item.get("answerable", True)
        if not isinstance(answerable, bool):
            raise ValueError("Retrieval dataset answerable must be a boolean")
        source_name = item.get("expected_source_name")
        document_title = item.get("expected_document_title")
        case = RetrievalEvaluationCase(
            id=str(item["id"]).strip(),
            query=str(item["query"]).strip(),
            answerable=answerable,
            expected_source_name=(None if source_name is None else str(source_name).strip()),
            expected_document_title=(
                None if document_title is None else str(document_title).strip()
            ),
        )
        if not case.id or not case.query:
            raise ValueError("Retrieval dataset cases cannot contain blank fields")
        if case.answerable and (not case.expected_source_name or not case.expected_document_title):
            raise ValueError("Answerable evaluation cases require an expected Document")
        if not case.answerable and (
            case.expected_source_name is not None or case.expected_document_title is not None
        ):
            raise ValueError("Negative evaluation cases cannot name an expected Document")
        cases.append(case)
    cases = tuple(cases)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Retrieval dataset case IDs must be unique")
    return version, cases


def resolve_expected_documents(
    cases: tuple[RetrievalEvaluationCase, ...],
    documents: tuple[DocumentSummaryView, ...],
) -> tuple[ResolvedRetrievalEvaluationCase, ...]:
    """Resolve human-maintainable source keys to unambiguous database UUIDs."""
    documents_by_key: dict[tuple[str, str], list[UUID]] = {}
    for document in documents:
        key = (document.source_name, document.title)
        documents_by_key.setdefault(key, []).append(document.id)

    resolved = []
    for case in cases:
        if not case.answerable:
            resolved.append(
                ResolvedRetrievalEvaluationCase(
                    id=case.id,
                    query=case.query,
                    answerable=False,
                    expected_document_id=None,
                )
            )
            continue
        assert case.expected_source_name is not None
        assert case.expected_document_title is not None
        key = (case.expected_source_name, case.expected_document_title)
        document_ids = documents_by_key.get(key, [])
        if len(document_ids) != 1:
            raise ValueError(
                f"Evaluation case {case.id!r} expected exactly one Document for "
                f"source/title key {key!r}, found {len(document_ids)}"
            )
        resolved.append(
            ResolvedRetrievalEvaluationCase(
                id=case.id,
                query=case.query,
                answerable=True,
                expected_document_id=document_ids[0],
            )
        )
    return tuple(resolved)


async def evaluate_retrieval(
    retriever: KnowledgeRetriever,
    *,
    dataset_version: str,
    cases: tuple[ResolvedRetrievalEvaluationCase, ...],
    user_role: str,
    relevance_policy: RelevancePolicy,
) -> RetrievalEvaluationReport:
    """Run retrieval once and derive recall plus gate-level answer/refusal proxies."""
    if not cases:
        raise ValueError("Retrieval evaluation requires at least one case")
    case_results = []
    for case in cases:
        search_results = await retriever.search(
            case.query,
            top_k=5,
            filters=SearchFilters(),
            user_context=UserContext(role=user_role),
        )
        relevant_results = relevance_policy.select(search_results)
        document_ids = tuple(result.document_id for result in relevant_results)
        titles = tuple(result.document_title for result in relevant_results)
        case_results.append(
            RetrievalCaseResult(
                id=case.id,
                expected_answerable=case.answerable,
                would_call_model=bool(relevant_results),
                hit_at_3=(case.answerable and case.expected_document_id in document_ids[:3]),
                hit_at_5=(case.answerable and case.expected_document_id in document_ids[:5]),
                retrieved_document_ids=document_ids,
                retrieved_document_titles=titles,
            )
        )
    total = len(case_results)
    positive_results = [result for result in case_results if result.expected_answerable]
    negative_results = [result for result in case_results if not result.expected_answerable]
    positive_total = len(positive_results)
    negative_total = len(negative_results)
    return RetrievalEvaluationReport(
        dataset_version=dataset_version,
        total_cases=total,
        positive_cases=positive_total,
        negative_cases=negative_total,
        recall_at_3=(
            sum(result.hit_at_3 for result in positive_results) / positive_total
            if positive_total
            else 0.0
        ),
        recall_at_5=(
            sum(result.hit_at_5 for result in positive_results) / positive_total
            if positive_total
            else 0.0
        ),
        false_answer_rate=(
            sum(result.would_call_model for result in negative_results) / negative_total
            if negative_total
            else 0.0
        ),
        abstention_accuracy=(
            sum(not result.would_call_model for result in negative_results) / negative_total
            if negative_total
            else 0.0
        ),
        results=tuple(case_results),
    )
