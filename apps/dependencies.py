"""Shared application-service construction for API and CLI entry points."""

import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.intelligence.embeddings import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from enterprise_it_support.intelligence.model_gateway import (
    FakeModelCall,
    FakeModelGateway,
    ModelGateway,
    OpenAICompatibleModelGateway,
)
from enterprise_it_support.knowledge.indexing import (
    EmbeddingProfile,
    IndexingRepository,
    IndexingService,
)
from enterprise_it_support.knowledge.retrieval import KnowledgeRetriever, RetrievalRepository
from enterprise_it_support.platform.config import (
    EmbeddingProviderType,
    ModelProviderType,
    Settings,
)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured adapter without exposing credentials to business code."""
    if settings.embedding_provider is EmbeddingProviderType.FAKE:
        return FakeEmbeddingProvider(dimension=settings.embedding_dimension)

    assert settings.embedding_api_key is not None
    return OpenAIEmbeddingProvider(
        api_key=settings.embedding_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        base_url=settings.embedding_base_url,
    )


def build_indexing_service(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> IndexingService:
    """Build indexing with one immutable Profile from validated Settings."""
    return IndexingService(
        repository=IndexingRepository(session_factory),
        provider=build_embedding_provider(settings),
        profile=EmbeddingProfile(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            version=settings.embedding_version,
        ),
        batch_size=settings.embedding_batch_size,
    )


def build_knowledge_retriever(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> KnowledgeRetriever:
    """Build authorized hybrid retrieval with the configured Embedding Profile."""
    return KnowledgeRetriever(
        repository=RetrievalRepository(session_factory),
        provider=build_embedding_provider(settings),
        profile=EmbeddingProfile(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            version=settings.embedding_version,
        ),
        embedding_timeout_seconds=settings.retrieval_embedding_timeout_seconds,
    )


def build_model_gateway(settings: Settings) -> ModelGateway:
    """Build the bounded structured chat-model adapter from validated Settings."""
    if settings.model_provider is ModelProviderType.FAKE:
        return FakeModelGateway(
            [],
            model_name=settings.model_name,
            response_factory=_fake_rag_response,
        )

    assert settings.model_api_key is not None
    return OpenAICompatibleModelGateway(
        api_key=settings.model_api_key.get_secret_value(),
        base_url=settings.model_base_url,
        model=settings.model_name,
        timeout_seconds=settings.model_timeout_seconds,
        max_attempts=settings.model_max_attempts,
        max_output_tokens=settings.model_max_output_tokens,
    )


def _fake_rag_response(call: FakeModelCall) -> dict[str, object]:
    """Produce a repeatable grounded local demo response from the first Context item."""
    try:
        payload = json.loads(call.messages[-1].content)
        context = payload["context"]
        evidence = context[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exception:
        raise ValueError("Fake RAG model received an invalid Context payload") from exception

    content = " ".join(str(evidence["content"]).split())
    document_title = str(evidence["document_title"])
    return {
        "summary": f"来自 {document_title} 的知识库回答",
        "answer": f"企业知识库片段说明: {content[:1200]}",
        "diagnosis": [f"企业知识库: 已检索到 {document_title} 的相关片段."],
        "evidence_ids": [str(evidence["evidence_id"])],
        "limitations": ["Fake model 仅用于本地演示结构化 RAG 流程."],
        "next_steps": ["企业知识库: 请按照引用片段操作并核对结果."],
        "confidence": 0.75,
        "answerable": True,
    }
