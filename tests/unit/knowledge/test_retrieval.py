"""Deterministic tests for the public hybrid retrieval interface."""

import asyncio
from collections.abc import Sequence
from uuid import UUID

import pytest

from enterprise_it_support.intelligence.embeddings import EmbeddingProviderError
from enterprise_it_support.knowledge.indexing import EmbeddingProfile
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    RetrievalCandidate,
    RetrievalMethod,
    RetrievalUnavailableError,
    SearchFilters,
    UserContext,
)


class FixedQueryProvider:
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


class InvalidQueryProvider(FixedQueryProvider):
    def __init__(self, response: list[float] | Exception, delay: float = 0.0) -> None:
        self._response = response
        self._delay = delay

    async def embed_query(self, text: str) -> list[float]:
        if self._delay:
            await asyncio.sleep(self._delay)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FixedRetrievalRepository:
    def __init__(
        self,
        keyword: tuple[RetrievalCandidate, ...],
        vector: tuple[RetrievalCandidate, ...],
    ) -> None:
        self._keyword = keyword
        self._vector = vector

    async def search_keyword(self, *args, **kwargs) -> tuple[RetrievalCandidate, ...]:
        return self._keyword[: kwargs["limit"]]

    async def search_vector(self, *args, **kwargs) -> tuple[RetrievalCandidate, ...]:
        return self._vector[: kwargs["limit"]]


def _candidate(
    chunk_id: str,
    method: RetrievalMethod,
    *,
    title: str = "VPN Guide",
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=UUID(chunk_id),
        document_id=UUID("10000000-0000-0000-0000-000000000001"),
        document_title=title,
        document_version=2,
        content="Traceable fictional support content",
        section_title="Troubleshooting",
        score=0.9,
        retrieval_method=method,
    )


@pytest.mark.asyncio
async def test_hybrid_search_uses_rrf_deduplicates_and_honors_top_k() -> None:
    shared_keyword = _candidate(
        "00000000-0000-0000-0000-000000000001",
        RetrievalMethod.KEYWORD,
    )
    keyword_only = _candidate(
        "00000000-0000-0000-0000-000000000002",
        RetrievalMethod.KEYWORD,
    )
    shared_vector = _candidate(
        "00000000-0000-0000-0000-000000000001",
        RetrievalMethod.VECTOR,
    )
    vector_only = _candidate(
        "00000000-0000-0000-0000-000000000003",
        RetrievalMethod.VECTOR,
    )
    retriever = KnowledgeRetriever(
        repository=FixedRetrievalRepository(
            (shared_keyword, keyword_only),
            (shared_vector, vector_only),
        ),
        provider=FixedQueryProvider(),
        profile=EmbeddingProfile(model="fixed", dimension=2, version="v1"),
    )

    results = await retriever.search(
        "VPN timeout",
        top_k=2,
        filters=SearchFilters(),
        user_context=UserContext(role="employee"),
    )

    assert len(results) == 2
    assert len({result.chunk_id for result in results}) == 2
    assert results[0].chunk_id == shared_keyword.chunk_id
    assert results[0].retrieval_method is RetrievalMethod.HYBRID
    assert results[0].rrf_score == pytest.approx(2 / 61)
    assert results[0].keyword_score == 0.9
    assert results[0].vector_similarity == 0.9
    assert results[0].citation.chunk_id == results[0].chunk_id
    assert results[0].citation.document_title == "VPN Guide"
    assert results[0].citation.document_version == 2
    assert results[0].citation.section_title == "Troubleshooting"


@pytest.mark.asyncio
async def test_hybrid_search_returns_empty_when_both_strategies_have_no_candidates() -> None:
    retriever = KnowledgeRetriever(
        repository=FixedRetrievalRepository((), ()),
        provider=FixedQueryProvider(),
        profile=EmbeddingProfile(model="fixed", dimension=2, version="v1"),
    )

    results = await retriever.search(
        "no matching evidence",
        top_k=5,
        filters=SearchFilters(),
        user_context=UserContext(role="employee"),
    )

    assert results == ()


@pytest.mark.asyncio
async def test_search_rejects_nonpositive_top_k() -> None:
    retriever = KnowledgeRetriever(
        repository=FixedRetrievalRepository((), ()),
        provider=FixedQueryProvider(),
        profile=EmbeddingProfile(model="fixed", dimension=2, version="v1"),
    )

    with pytest.raises(ValueError, match="top_k"):
        await retriever.search(
            "VPN",
            top_k=0,
            filters=SearchFilters(),
            user_context=UserContext(role="employee"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "message"),
    [
        (InvalidQueryProvider([0.0, 0.0]), "zero vector"),
        (InvalidQueryProvider([1.0]), "dimension"),
        (InvalidQueryProvider([float("nan"), 1.0]), "non-finite"),
        (InvalidQueryProvider(["not-a-number", 1.0]), "malformed"),
        (
            InvalidQueryProvider(EmbeddingProviderError("secret provider detail")),
            "embedding failed",
        ),
    ],
)
async def test_search_maps_unusable_provider_outputs_to_retrieval_unavailable(
    provider: InvalidQueryProvider,
    message: str,
) -> None:
    retriever = KnowledgeRetriever(
        repository=FixedRetrievalRepository((), ()),
        provider=provider,
        profile=EmbeddingProfile(model="fixed", dimension=2, version="v1"),
    )

    with pytest.raises(RetrievalUnavailableError, match=message):
        await retriever.search(
            "VPN",
            top_k=1,
            filters=SearchFilters(),
            user_context=UserContext(role="employee"),
        )


@pytest.mark.asyncio
async def test_search_times_out_slow_query_embedding() -> None:
    retriever = KnowledgeRetriever(
        repository=FixedRetrievalRepository((), ()),
        provider=InvalidQueryProvider([1.0, 0.0], delay=0.05),
        profile=EmbeddingProfile(model="fixed", dimension=2, version="v1"),
        embedding_timeout_seconds=0.001,
    )

    with pytest.raises(RetrievalUnavailableError, match="timed out"):
        await retriever.search(
            "VPN",
            top_k=1,
            filters=SearchFilters(),
            user_context=UserContext(role="employee"),
        )
