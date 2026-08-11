"""Deterministic Recall@K evaluation for the public retrieval interface."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from enterprise_it_support.knowledge.domain import DocumentSummaryView
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    SearchFilters,
    UserContext,
)


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """One query and the stable source identity of its expected Document."""

    id: str
    query: str
    expected_source_name: str
    expected_document_title: str


@dataclass(frozen=True)
class ResolvedRetrievalEvaluationCase:
    """Evaluation case whose expected source has been resolved to a Document UUID."""

    id: str
    query: str
    expected_document_id: UUID


@dataclass(frozen=True)
class RetrievalCaseResult:
    """Per-query hit outcome at the two required cutoffs."""

    id: str
    hit_at_3: bool
    hit_at_5: bool
    retrieved_document_ids: tuple[UUID, ...]
    retrieved_document_titles: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluationReport:
    """Aggregate Recall@3 and Recall@5 plus inspectable failures."""

    dataset_version: str
    total_cases: int
    recall_at_3: float
    recall_at_5: float
    results: tuple[RetrievalCaseResult, ...]

    @property
    def missed_at_3(self) -> tuple[str, ...]:
        return tuple(result.id for result in self.results if not result.hit_at_3)

    @property
    def missed_at_5(self) -> tuple[str, ...]:
        return tuple(result.id for result in self.results if not result.hit_at_5)


def load_retrieval_dataset(
    path: Path,
) -> tuple[str, tuple[RetrievalEvaluationCase, ...]]:
    """Load a versioned JSON retrieval dataset with basic integrity checks."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = str(raw.get("version", "")).strip()
    raw_cases = raw.get("cases")
    if not version or not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Retrieval dataset must contain a version and non-empty cases")
    cases = tuple(
        RetrievalEvaluationCase(
            id=str(item["id"]).strip(),
            query=str(item["query"]).strip(),
            expected_source_name=str(item["expected_source_name"]).strip(),
            expected_document_title=str(item["expected_document_title"]).strip(),
        )
        for item in raw_cases
    )
    if any(
        not case.id
        or not case.query
        or not case.expected_source_name
        or not case.expected_document_title
        for case in cases
    ):
        raise ValueError("Retrieval dataset cases cannot contain blank fields")
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
) -> RetrievalEvaluationReport:
    """Run all cases once at top-5 and derive Recall@3 and Recall@5."""
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
        document_ids = tuple(result.document_id for result in search_results)
        titles = tuple(result.document_title for result in search_results)
        case_results.append(
            RetrievalCaseResult(
                id=case.id,
                hit_at_3=case.expected_document_id in document_ids[:3],
                hit_at_5=case.expected_document_id in document_ids[:5],
                retrieved_document_ids=document_ids,
                retrieved_document_titles=titles,
            )
        )
    total = len(case_results)
    return RetrievalEvaluationReport(
        dataset_version=dataset_version,
        total_cases=total,
        recall_at_3=sum(result.hit_at_3 for result in case_results) / total,
        recall_at_5=sum(result.hit_at_5 for result in case_results) / total,
        results=tuple(case_results),
    )
