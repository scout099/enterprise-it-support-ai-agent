"""Chunk embedding indexing tests against PostgreSQL."""

import json
import logging
from argparse import Namespace
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from scripts.index_documents import run as run_index_cli
from sqlalchemy import func, select, text

from enterprise_it_support.intelligence.embeddings import (
    EmbeddingProviderError,
    FakeEmbeddingProvider,
)
from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.indexing import (
    EmbeddingProfile,
    IndexingRepository,
    IndexingService,
)
from enterprise_it_support.knowledge.models import DocumentChunk
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.knowledge.service import DocumentIngestionService, LocalDocumentStorage
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

FIXTURES = Path(__file__).parents[3] / "data" / "evaluation" / "knowledge"


@dataclass(frozen=True)
class IndexingEnvironment:
    ingestion: DocumentIngestionService
    indexing: IndexingService
    repository: IndexingRepository
    database: DatabaseManager


class WrongDimensionProvider:
    """External-boundary fake that violates the configured vector dimension."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] * 7 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * 7


class ZeroVectorProvider:
    """External-boundary fake that returns cosine-undefined vectors."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * 8


class FailingOnceProvider:
    """External-boundary fake that makes only its first batch fail."""

    def __init__(self) -> None:
        self._calls = 0
        self._fallback = FakeEmbeddingProvider(dimension=8)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self._calls += 1
        if self._calls == 1:
            raise EmbeddingProviderError("Fictional provider outage")
        return await self._fallback.embed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._fallback.embed_query(text)


@pytest.fixture
async def indexing_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[IndexingEnvironment]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory.begin() as session:
        await session.execute(
            text(
                "TRUNCATE document_chunks, document_versions, documents, knowledge_sources CASCADE"
            )
        )

    ingestion = DocumentIngestionService(
        repository=KnowledgeRepository(database.session_factory),
        parser_registry=DocumentParserRegistry(),
        chunker=DocumentChunker(chunk_size=20, chunk_overlap=4),
        storage=LocalDocumentStorage(tmp_path),
        max_file_size_bytes=1_000_000,
    )
    indexing_repository = IndexingRepository(database.session_factory)
    indexing = IndexingService(
        repository=indexing_repository,
        provider=FakeEmbeddingProvider(dimension=8),
        profile=EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v1"),
        batch_size=2,
    )

    yield IndexingEnvironment(
        ingestion=ingestion,
        indexing=indexing,
        repository=indexing_repository,
        database=database,
    )

    await database.close()
    get_settings.cache_clear()


@pytest.mark.integration
async def test_indexes_document_chunks_in_batches(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="VPN Indexing SOP",
        owner="Demo IT Operations",
        source_name="Indexing Test Library",
    )

    result = await indexing_environment.indexing.index_document(imported.document_id)
    status = await indexing_environment.indexing.get_status(imported.document_id)

    assert result.indexed_chunks == imported.chunk_count
    assert result.skipped_chunks == 0
    assert result.failed_chunks == 0
    assert result.successful_batches >= 2
    assert result.failed_batches == 0
    assert status.total_chunks == imported.chunk_count
    assert status.indexed_chunks == imported.chunk_count
    assert status.pending_chunks == 0
    assert status.stale_chunks == 0
    assert status.status == "indexed"


@pytest.mark.integration
async def test_repeated_index_skips_current_chunks_unless_forced(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Outlook Indexing SOP",
        owner="Demo Messaging Team",
        source_name="Indexing Test Library",
    )
    await indexing_environment.indexing.index_document(imported.document_id)

    repeated = await indexing_environment.indexing.index_document(imported.document_id)
    forced = await indexing_environment.indexing.index_document(
        imported.document_id,
        force=True,
    )

    assert repeated.indexed_chunks == 0
    assert repeated.skipped_chunks == imported.chunk_count
    assert repeated.successful_batches == 0
    assert forced.indexed_chunks == imported.chunk_count
    assert forced.skipped_chunks == 0


@pytest.mark.integration
async def test_embedding_profile_version_change_marks_chunks_stale_and_reindexes(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "account_common_questions_faq.pdf"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Profile Version Account FAQ",
        owner="Demo Identity Team",
        source_name="Indexing Test Library",
    )
    await indexing_environment.indexing.index_document(imported.document_id)
    version_two = IndexingService(
        repository=indexing_environment.repository,
        provider=FakeEmbeddingProvider(dimension=8),
        profile=EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v2"),
        batch_size=2,
    )

    stale_status = await version_two.get_status(imported.document_id)
    result = await version_two.index_document(imported.document_id)
    current_status = await version_two.get_status(imported.document_id)

    assert stale_status.status == "stale"
    assert stale_status.stale_chunks == imported.chunk_count
    assert result.indexed_chunks == imported.chunk_count
    assert result.skipped_chunks == 0
    assert current_status.status == "indexed"
    assert current_status.stale_chunks == 0


@pytest.mark.integration
async def test_document_update_indexes_only_new_version_chunks(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    original_data = path.read_bytes()
    first = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=original_data,
        title="Versioned VPN Indexing SOP",
        owner="Demo IT Operations",
        source_name="Indexing Test Library",
    )
    await indexing_environment.indexing.index_document(first.document_id)
    changed_data = original_data.replace(
        b"Escalate after three failed attempts.",
        b"Escalate after two failed attempts and retain the fictional diagnostic code.",
    )
    second = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=changed_data,
        title="Versioned VPN Indexing SOP",
        owner="Demo IT Operations",
        source_name="Indexing Test Library",
    )

    update_result = await indexing_environment.indexing.index_document(first.document_id)
    status = await indexing_environment.indexing.get_status(first.document_id)

    assert second.version == 2
    assert update_result.indexed_chunks == second.chunk_count
    assert update_result.skipped_chunks == first.chunk_count
    assert status.total_chunks == first.chunk_count + second.chunk_count
    assert status.indexed_chunks == status.total_chunks
    assert status.status == "indexed"


@pytest.mark.integration
async def test_wrong_embedding_dimension_leaves_batch_pending(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Dimension Validation SOP",
        owner="Demo Messaging Team",
        source_name="Indexing Test Library",
    )
    invalid_service = IndexingService(
        repository=indexing_environment.repository,
        provider=WrongDimensionProvider(),
        profile=EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v1"),
        batch_size=2,
    )

    result = await invalid_service.index_document(imported.document_id)
    status = await invalid_service.get_status(imported.document_id)

    assert result.indexed_chunks == 0
    assert result.failed_chunks == imported.chunk_count
    assert result.failed_batches > 0
    assert status.indexed_chunks == 0
    assert status.pending_chunks == imported.chunk_count
    assert status.status == "pending"


@pytest.mark.integration
async def test_zero_embedding_vector_leaves_batch_pending(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Zero Vector Validation SOP",
        owner="Demo Messaging Team",
        source_name="Indexing Test Library",
    )
    invalid_service = IndexingService(
        repository=indexing_environment.repository,
        provider=ZeroVectorProvider(),
        profile=EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v1"),
        batch_size=2,
    )

    result = await invalid_service.index_document(imported.document_id)
    status = await invalid_service.get_status(imported.document_id)

    assert result.indexed_chunks == 0
    assert result.failed_chunks == imported.chunk_count
    assert status.indexed_chunks == 0
    assert status.pending_chunks == imported.chunk_count


@pytest.mark.integration
async def test_provider_batch_failure_preserves_later_batches_and_can_retry(
    indexing_environment: IndexingEnvironment,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Retryable VPN Indexing SOP",
        owner="Demo IT Operations",
        source_name="Indexing Test Library",
    )
    service = IndexingService(
        repository=indexing_environment.repository,
        provider=FailingOnceProvider(),
        profile=EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v1"),
        batch_size=1,
    )

    with caplog.at_level(logging.ERROR, logger="enterprise_it_support.knowledge.indexing"):
        first_result = await service.index_document(imported.document_id)
    partial_status = await service.get_status(imported.document_id)
    retry_result = await service.index_document(imported.document_id)
    final_status = await service.get_status(imported.document_id)

    assert first_result.failed_chunks == 1
    assert first_result.indexed_chunks == imported.chunk_count - 1
    assert partial_status.status == "partial"
    assert partial_status.pending_chunks == 1
    assert "embedding_batch_failed" in caplog.text
    assert "Fictional provider outage" not in caplog.text
    assert retry_result.indexed_chunks == 1
    assert final_status.status == "indexed"
    assert final_status.indexed_chunks == imported.chunk_count


@pytest.mark.integration
async def test_pgvector_stores_and_orders_vectors_by_cosine_distance(
    indexing_environment: IndexingEnvironment,
) -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Vector Query Verification SOP",
        owner="Demo Messaging Team",
        source_name="Indexing Test Library",
    )
    await indexing_environment.indexing.index_document(imported.document_id)
    chunks = await indexing_environment.ingestion.get_latest_chunks(imported.document_id)
    target = chunks.chunks[0]
    query_vector = await FakeEmbeddingProvider(dimension=8).embed_query(target.content)

    async with indexing_environment.database.session_factory() as session:
        nearest_chunk_id = await session.scalar(
            select(DocumentChunk.id)
            .where(DocumentChunk.document_version_id == imported.document_version_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        stored_dimension = await session.scalar(
            select(func.vector_dims(DocumentChunk.embedding)).where(DocumentChunk.id == target.id)
        )

    assert nearest_chunk_id == target.id
    assert stored_dimension == 8


@pytest.mark.integration
async def test_cli_indexes_all_pending_documents(
    indexing_environment: IndexingEnvironment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = FIXTURES / "account_common_questions_faq.pdf"
    imported = await indexing_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Account FAQ CLI Indexing",
        owner="Demo Identity Team",
        source_name="Indexing Test Library",
    )
    settings = Settings(environment=Environment.TEST).model_copy(
        update={
            "embedding_model": "fake-embedding-v1",
            "embedding_dimension": 8,
            "embedding_version": "v1",
            "embedding_batch_size": 2,
        }
    )

    exit_code = await run_index_cli(
        Namespace(document_id=None, force=False),
        settings=settings,
    )
    output = json.loads(capsys.readouterr().out.splitlines()[-1])
    status = await indexing_environment.indexing.get_status(imported.document_id)

    assert exit_code == 0
    assert output["document_count"] == 1
    assert output["indexed_chunks"] == imported.chunk_count
    assert output["failed_chunks"] == 0
    assert status.status == "indexed"
