"""Authorized PostgreSQL keyword, vector, and hybrid knowledge retrieval."""

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from sqlalchemy import and_, any_, func, literal, literal_column, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.intelligence.embeddings import EmbeddingProvider, EmbeddingProviderError
from enterprise_it_support.knowledge.domain import DocumentSourceType, DocumentStatus
from enterprise_it_support.knowledge.indexing import EmbeddingProfile
from enterprise_it_support.knowledge.models import Document, DocumentChunk, DocumentVersion

# Versioned English question-word filter calibrated only for the Phase 5 demo corpus.
# It deliberately changes query parsing, not evidence scoring, and must be reevaluated
# before adding another language or materially different enterprise corpus.
_ENGLISH_QUESTION_STOP_WORDS_V1 = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "company",
        "do",
        "does",
        "for",
        "how",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "should",
        "the",
        "to",
        "use",
        "what",
        "when",
        "which",
    }
)
_MIN_KEYWORD_TERM_LENGTH = 2


def extract_keyword_terms(text: str) -> tuple[str, ...]:
    """Extract the versioned deterministic terms used by the demo keyword query."""
    return tuple(
        term
        for term in re.findall(r"[^\W_]+", text.casefold())
        if len(term) >= _MIN_KEYWORD_TERM_LENGTH and term not in _ENGLISH_QUESTION_STOP_WORDS_V1
    )


class RetrievalMethod(StrEnum):
    """How a returned Chunk entered the final ranking."""

    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"


class RetrievalUnavailableError(RuntimeError):
    """Raised when retrieval cannot safely produce a ranked result."""


@dataclass(frozen=True)
class SearchFilters:
    """Allowlisted document and validity filters for retrieval."""

    document_id: UUID | None = None
    document_ids: frozenset[UUID] | None = None
    source_type: DocumentSourceType | None = None
    status: DocumentStatus | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.document_id is not None and self.document_ids is not None:
            raise ValueError("document_id and document_ids filters are mutually exclusive")
        if self.document_ids is not None and not self.document_ids:
            raise ValueError("document_ids filter cannot be empty")
        for field_name, value in (
            ("effective_at", self.effective_at),
            ("expires_at", self.expires_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must include a timezone")


@dataclass(frozen=True)
class UserContext:
    """Minimal caller identity used by deterministic retrieval authorization."""

    role: str

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("User role cannot be empty")


@dataclass(frozen=True)
class Citation:
    """Stable source identity attached to one retrieved Chunk."""

    document_title: str
    document_version: int
    section_title: str | None
    chunk_id: UUID


@dataclass(frozen=True)
class SearchResult:
    """Public retrieval result with content, rank evidence, and citation."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version: int
    content: str
    section_title: str | None
    rrf_score: float
    keyword_score: float | None
    vector_similarity: float | None
    retrieval_method: RetrievalMethod
    citation: Citation


@dataclass(frozen=True)
class RelevancePolicy:
    """Select evidence using calibrated raw retrieval signals, never fused rank."""

    min_keyword_score: float
    min_vector_similarity: float | None

    def __post_init__(self) -> None:
        if self.min_keyword_score < 0:
            raise ValueError("Minimum keyword score cannot be negative")
        if self.min_vector_similarity is not None and not (-1 <= self.min_vector_similarity <= 1):
            raise ValueError("Minimum vector similarity must be between -1 and 1")

    def select(self, results: tuple[SearchResult, ...]) -> tuple[SearchResult, ...]:
        """Preserve retrieval order while dropping results below every enabled threshold."""
        return tuple(result for result in results if self.accepts(result))

    def accepts(self, result: SearchResult) -> bool:
        """Return whether any calibrated raw signal is strong enough."""
        keyword_relevant = (
            result.keyword_score is not None and result.keyword_score >= self.min_keyword_score
        )
        vector_relevant = (
            self.min_vector_similarity is not None
            and result.vector_similarity is not None
            and result.vector_similarity >= self.min_vector_similarity
        )
        return keyword_relevant or vector_relevant


@dataclass(frozen=True)
class RetrievalCandidate:
    """One ranked result from a single PostgreSQL retrieval strategy."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version: int
    content: str
    section_title: str | None
    score: float
    retrieval_method: RetrievalMethod

    def to_search_result(
        self,
        *,
        rrf_score: float,
        keyword_score: float | None,
        vector_similarity: float | None,
        retrieval_method: RetrievalMethod,
    ) -> SearchResult:
        return SearchResult(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            document_title=self.document_title,
            document_version=self.document_version,
            content=self.content,
            section_title=self.section_title,
            rrf_score=rrf_score,
            keyword_score=keyword_score,
            vector_similarity=vector_similarity,
            retrieval_method=retrieval_method,
            citation=Citation(
                document_title=self.document_title,
                document_version=self.document_version,
                section_title=self.section_title,
                chunk_id=self.chunk_id,
            ),
        )


class RetrievalRepository:
    """Own authorized PostgreSQL FTS and pgvector candidate queries."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search_keyword(
        self,
        query: str,
        *,
        limit: int,
        filters: SearchFilters,
        user_context: UserContext,
        now: datetime,
    ) -> tuple[RetrievalCandidate, ...]:
        """Rank current authorized Chunks with PostgreSQL full-text search."""
        search_document = (
            func.coalesce(DocumentChunk.section_title, literal_column("''"))
            + literal_column("' '")
            + DocumentChunk.content
        )
        search_vector = func.to_tsvector("simple", search_document)
        search_query = func.websearch_to_tsquery("simple", self._keyword_query_text(query))
        keyword_score = func.ts_rank_cd(search_vector, search_query).label("score")
        statement = (
            self._candidate_statement(filters, user_context, now)
            .add_columns(keyword_score)
            .where(search_vector.op("@@")(search_query))
            .order_by(keyword_score.desc(), DocumentChunk.id)
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        return tuple(self._candidate_from_row(row, RetrievalMethod.KEYWORD) for row in rows)

    @staticmethod
    def _keyword_query_text(query: str) -> str:
        """Build deterministic any-term FTS input without trusting websearch operators."""
        terms = extract_keyword_terms(query)
        if not terms:
            return "__no_meaningful_search_terms__"
        return " OR ".join(terms)

    async def search_vector(
        self,
        query_vector: list[float],
        *,
        profile: EmbeddingProfile,
        limit: int,
        filters: SearchFilters,
        user_context: UserContext,
        now: datetime,
    ) -> tuple[RetrievalCandidate, ...]:
        """Rank current authorized Chunks by exact pgvector cosine distance."""
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            self._candidate_statement(filters, user_context, now)
            .add_columns(distance)
            .where(
                DocumentChunk.embedding.is_not(None),
                DocumentChunk.embedding_model == profile.model,
                DocumentChunk.embedding_version == profile.version,
                func.vector_dims(DocumentChunk.embedding) == profile.dimension,
            )
            .order_by(distance, DocumentChunk.id)
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        candidates = []
        for row in rows:
            raw_distance = row[-1]
            if raw_distance is None or not isfinite(float(raw_distance)):
                continue
            similarity = max(-1.0, min(1.0, 1.0 - float(raw_distance)))
            candidates.append(
                self._candidate_from_row((*row[:-1], similarity), RetrievalMethod.VECTOR)
            )
        return tuple(candidates)

    @staticmethod
    def _candidate_statement(
        filters: SearchFilters,
        user_context: UserContext,
        now: datetime,
    ):
        requested_status = filters.status or DocumentStatus.ACTIVE
        visibility_filter = or_(
            Document.visibility == "public",
            and_(
                Document.visibility == "role_restricted",
                literal(user_context.role) == any_(Document.allowed_roles),
            ),
        )
        version_rank = func.row_number().over(
            partition_by=DocumentVersion.document_id,
            order_by=DocumentVersion.version.desc(),
        )
        eligible_versions = (
            select(
                DocumentVersion.id.label("document_version_id"),
                version_rank.label("version_rank"),
            )
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Document.status == requested_status.value,
                DocumentVersion.effective_at <= now,
                or_(
                    DocumentVersion.expires_at.is_(None),
                    DocumentVersion.expires_at > now,
                ),
                visibility_filter,
            )
        )
        if filters.effective_at is not None:
            eligible_versions = eligible_versions.where(
                DocumentVersion.effective_at <= filters.effective_at
            )
        if filters.expires_at is not None:
            eligible_versions = eligible_versions.where(
                or_(
                    DocumentVersion.expires_at.is_(None),
                    DocumentVersion.expires_at > filters.expires_at,
                )
            )
        if filters.document_id is not None:
            eligible_versions = eligible_versions.where(Document.id == filters.document_id)
        if filters.document_ids is not None:
            eligible_versions = eligible_versions.where(Document.id.in_(filters.document_ids))
        if filters.source_type is not None:
            eligible_versions = eligible_versions.where(
                Document.source_type == filters.source_type.value
            )
        latest_eligible = eligible_versions.subquery()
        return (
            select(
                DocumentChunk.id,
                Document.id,
                Document.title,
                DocumentVersion.version,
                DocumentChunk.content,
                DocumentChunk.section_title,
            )
            .join(
                latest_eligible,
                latest_eligible.c.document_version_id == DocumentChunk.document_version_id,
            )
            .join(
                DocumentVersion,
                DocumentVersion.id == DocumentChunk.document_version_id,
            )
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(latest_eligible.c.version_rank == 1)
        )

    @staticmethod
    def _candidate_from_row(row, method: RetrievalMethod) -> RetrievalCandidate:
        return RetrievalCandidate(
            chunk_id=row[0],
            document_id=row[1],
            document_title=row[2],
            document_version=row[3],
            content=row[4],
            section_title=row[5],
            score=float(row[6]),
            retrieval_method=method,
        )


class KnowledgeRetriever:
    """Unified hybrid retrieval interface with pre-query authorization."""

    def __init__(
        self,
        *,
        repository: RetrievalRepository,
        provider: EmbeddingProvider,
        profile: EmbeddingProfile,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        embedding_timeout_seconds: float = 10.0,
    ) -> None:
        if profile.dimension < 1:
            raise ValueError("Embedding dimension must be positive")
        if rrf_k < 1:
            raise ValueError("RRF k must be positive")
        if candidate_multiplier < 1:
            raise ValueError("Candidate multiplier must be positive")
        if embedding_timeout_seconds <= 0:
            raise ValueError("Embedding timeout must be positive")
        self._repository = repository
        self._provider = provider
        self._profile = profile
        self._rrf_k = rrf_k
        self._candidate_multiplier = candidate_multiplier
        self._embedding_timeout_seconds = embedding_timeout_seconds

    async def search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters,
        user_context: UserContext,
    ) -> tuple[SearchResult, ...]:
        """Return deduplicated hybrid results without generating an answer."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        try:
            query_vector = await asyncio.wait_for(
                self._provider.embed_query(normalized_query),
                timeout=self._embedding_timeout_seconds,
            )
        except TimeoutError as exception:
            raise RetrievalUnavailableError("Query embedding timed out") from exception
        except EmbeddingProviderError as exception:
            raise RetrievalUnavailableError("Query embedding failed") from exception
        query_vector = self._validate_query_vector(query_vector)
        candidate_limit = top_k * self._candidate_multiplier
        now = datetime.now(UTC)
        try:
            keyword_results, vector_results = await asyncio.gather(
                self._repository.search_keyword(
                    normalized_query,
                    limit=candidate_limit,
                    filters=filters,
                    user_context=user_context,
                    now=now,
                ),
                self._repository.search_vector(
                    query_vector,
                    profile=self._profile,
                    limit=candidate_limit,
                    filters=filters,
                    user_context=user_context,
                    now=now,
                ),
            )
        except SQLAlchemyError as exception:
            raise RetrievalUnavailableError("Knowledge database query failed") from exception
        return self._fuse(keyword_results, vector_results, top_k)

    def _validate_query_vector(self, vector: list[float]) -> list[float]:
        try:
            normalized = [float(value) for value in vector]
        except (TypeError, ValueError) as exception:
            raise RetrievalUnavailableError("Query embedding is malformed") from exception
        if len(normalized) != self._profile.dimension:
            raise RetrievalUnavailableError(
                "Embedding provider returned an unexpected query vector dimension"
            )
        if not all(isfinite(value) for value in normalized):
            raise RetrievalUnavailableError("Query embedding contains a non-finite value")
        if not any(value != 0.0 for value in normalized):
            raise RetrievalUnavailableError("Query embedding cannot be a zero vector")
        return normalized

    def _fuse(
        self,
        keyword_results: tuple[RetrievalCandidate, ...],
        vector_results: tuple[RetrievalCandidate, ...],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        candidates: dict[UUID, RetrievalCandidate] = {}
        rrf_scores: dict[UUID, float] = {}
        methods: dict[UUID, set[RetrievalMethod]] = {}
        keyword_scores: dict[UUID, float] = {}
        vector_similarities: dict[UUID, float] = {}
        for result_list in (keyword_results, vector_results):
            for rank, candidate in enumerate(result_list, start=1):
                candidates.setdefault(candidate.chunk_id, candidate)
                rrf_scores[candidate.chunk_id] = rrf_scores.get(candidate.chunk_id, 0.0) + 1.0 / (
                    self._rrf_k + rank
                )
                methods.setdefault(candidate.chunk_id, set()).add(candidate.retrieval_method)
                if candidate.retrieval_method is RetrievalMethod.KEYWORD:
                    keyword_scores[candidate.chunk_id] = candidate.score
                elif candidate.retrieval_method is RetrievalMethod.VECTOR:
                    vector_similarities[candidate.chunk_id] = candidate.score

        ranked_ids = sorted(
            rrf_scores,
            key=lambda chunk_id: (-rrf_scores[chunk_id], str(chunk_id)),
        )
        results = []
        for chunk_id in ranked_ids[:top_k]:
            method = (
                RetrievalMethod.HYBRID
                if len(methods[chunk_id]) > 1
                else next(iter(methods[chunk_id]))
            )
            candidate = replace(candidates[chunk_id], retrieval_method=method)
            results.append(
                candidate.to_search_result(
                    rrf_score=rrf_scores[chunk_id],
                    keyword_score=keyword_scores.get(chunk_id),
                    vector_similarity=vector_similarities.get(chunk_id),
                    retrieval_method=method,
                )
            )
        return tuple(results)
