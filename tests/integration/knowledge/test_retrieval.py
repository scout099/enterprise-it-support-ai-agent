"""Authorized keyword, vector, and hybrid retrieval tests against PostgreSQL."""

import json
from argparse import Namespace
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from scripts.evaluate_retrieval import run as run_retrieval_evaluation
from sqlalchemy import text, update

from enterprise_it_support.intelligence.embeddings import FakeEmbeddingProvider
from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.domain import DocumentSourceType, DocumentStatus
from enterprise_it_support.knowledge.indexing import (
    EmbeddingProfile,
    IndexingRepository,
    IndexingService,
)
from enterprise_it_support.knowledge.models import Document, DocumentChunk
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    RetrievalMethod,
    RetrievalRepository,
    SearchFilters,
    UserContext,
)
from enterprise_it_support.knowledge.service import DocumentIngestionService, LocalDocumentStorage
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

FIXTURES = Path(__file__).parents[2] / "fixtures" / "knowledge"
PROFILE = EmbeddingProfile(model="fake-embedding-v1", dimension=8, version="v1")


@dataclass(frozen=True)
class RetrievalEnvironment:
    ingestion: DocumentIngestionService
    indexing: IndexingService
    repository: RetrievalRepository
    retriever: KnowledgeRetriever
    provider: FakeEmbeddingProvider
    database: DatabaseManager


@pytest.fixture
async def retrieval_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[RetrievalEnvironment]:
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
    provider = FakeEmbeddingProvider(dimension=8)
    indexing = IndexingService(
        repository=IndexingRepository(database.session_factory),
        provider=provider,
        profile=PROFILE,
        batch_size=2,
    )
    repository = RetrievalRepository(database.session_factory)
    retriever = KnowledgeRetriever(
        repository=repository,
        provider=provider,
        profile=PROFILE,
    )

    yield RetrievalEnvironment(
        ingestion=ingestion,
        indexing=indexing,
        repository=repository,
        retriever=retriever,
        provider=provider,
        database=database,
    )

    await database.close()
    get_settings.cache_clear()


async def _import_and_index(
    environment: RetrievalEnvironment,
    filename: str,
    title: str,
    *,
    effective_at: datetime | None = None,
    expires_at: datetime | None = None,
):
    path = FIXTURES / filename
    imported = await environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title=title,
        owner="Demo IT Team",
        source_name="Retrieval Test Library",
        effective_at=effective_at,
        expires_at=expires_at,
    )
    await environment.indexing.index_document(imported.document_id)
    return imported


@pytest.mark.integration
async def test_postgresql_keyword_search_returns_matching_vpn_document(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "vpn_configuration_sop.md",
        "VPN Configuration SOP",
    )

    results = await retrieval_environment.repository.search_keyword(
        "VPN configuration",
        limit=5,
        filters=SearchFilters(),
        user_context=UserContext(role="employee"),
        now=datetime.now(UTC),
    )

    assert results
    assert results[0].document_id == imported.document_id
    assert results[0].retrieval_method is RetrievalMethod.KEYWORD


@pytest.mark.integration
async def test_pgvector_search_returns_exact_chunk_for_its_own_embedding(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "outlook_mail_troubleshooting.txt",
        "Outlook Mail Troubleshooting SOP",
    )
    chunks = await retrieval_environment.ingestion.get_latest_chunks(imported.document_id)
    target = chunks.chunks[0]
    query_vector = await retrieval_environment.provider.embed_query(target.content)

    results = await retrieval_environment.repository.search_vector(
        query_vector,
        profile=PROFILE,
        limit=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
        now=datetime.now(UTC),
    )

    assert results[0].chunk_id == target.id
    assert results[0].retrieval_method is RetrievalMethod.VECTOR


@pytest.mark.integration
async def test_pgvector_search_skips_cosine_undefined_stored_vectors(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "outlook_mail_troubleshooting.txt",
        "Zero Stored Vector SOP",
    )
    async with retrieval_environment.database.session_factory.begin() as session:
        await session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.document_version_id == imported.document_version_id)
            .values(embedding=[0.0] * PROFILE.dimension)
        )

    results = await retrieval_environment.repository.search_vector(
        [1.0] + [0.0] * (PROFILE.dimension - 1),
        profile=PROFILE,
        limit=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
        now=datetime.now(UTC),
    )

    assert results == ()


@pytest.mark.integration
async def test_hybrid_search_returns_ranked_results_with_complete_citations(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "outlook_mail_troubleshooting.txt",
        "Outlook Mail Troubleshooting SOP",
    )

    results = await retrieval_environment.retriever.search(
        "Outlook mailbox quota",
        top_k=3,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
    )

    assert results
    assert len(results) <= 3
    assert len({result.chunk_id for result in results}) == len(results)
    assert all(result.document_id == imported.document_id for result in results)
    assert all(result.citation.document_title == result.document_title for result in results)
    assert all(result.citation.document_version == result.document_version for result in results)
    assert all(result.citation.chunk_id == result.chunk_id for result in results)


@pytest.mark.integration
async def test_expired_document_is_excluded_by_default(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    now = datetime.now(UTC)
    imported = await _import_and_index(
        retrieval_environment,
        "vpn_configuration_sop.md",
        "Expired VPN Guide",
        effective_at=now - timedelta(days=30),
        expires_at=now - timedelta(days=1),
    )

    results = await retrieval_environment.retriever.search(
        "Expired VPN Guide",
        top_k=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
    )

    assert results == ()


@pytest.mark.integration
async def test_past_expires_filter_cannot_revive_currently_expired_document(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    now = datetime.now(UTC)
    imported = await _import_and_index(
        retrieval_environment,
        "vpn_configuration_sop.md",
        "Expired VPN Filter Guide",
        effective_at=now - timedelta(days=30),
        expires_at=now - timedelta(days=1),
    )

    results = await retrieval_environment.retriever.search(
        "VPN connection",
        top_k=5,
        filters=SearchFilters(
            document_id=imported.document_id,
            expires_at=now - timedelta(days=20),
        ),
        user_context=UserContext(role="employee"),
    )

    assert results == ()


@pytest.mark.integration
async def test_expires_filter_is_an_additional_minimum_validity_cutoff(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    now = datetime.now(UTC)
    imported = await _import_and_index(
        retrieval_environment,
        "vpn_configuration_sop.md",
        "Short Lived VPN Guide",
        expires_at=now + timedelta(days=1),
    )

    results = await retrieval_environment.retriever.search(
        "VPN connection",
        top_k=5,
        filters=SearchFilters(
            document_id=imported.document_id,
            expires_at=now + timedelta(days=2),
        ),
        user_context=UserContext(role="employee"),
    )

    assert results == ()


@pytest.mark.integration
async def test_latest_currently_effective_version_excludes_newer_future_version(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    first = await retrieval_environment.ingestion.ingest(
        filename=path.name,
        data=path.read_bytes(),
        title="Versioned Effective VPN Guide",
        owner="Demo IT Team",
        source_name="Retrieval Test Library",
    )
    changed_data = path.read_bytes().replace(
        b"Escalate after three failed attempts.",
        b"Escalate after nine failed attempts in this future version.",
    )
    second = await retrieval_environment.ingestion.ingest(
        filename=path.name,
        data=changed_data,
        title="Versioned Effective VPN Guide",
        owner="Demo IT Team",
        source_name="Retrieval Test Library",
        effective_at=datetime.now(UTC) + timedelta(days=1),
    )
    await retrieval_environment.indexing.index_document(first.document_id)

    results = await retrieval_environment.retriever.search(
        "VPN failed attempts",
        top_k=5,
        filters=SearchFilters(document_id=first.document_id),
        user_context=UserContext(role="employee"),
    )

    assert second.version == 2
    assert results
    assert {result.document_version for result in results} == {1}


@pytest.mark.integration
async def test_keyword_expression_uses_full_text_gin_index(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    async with retrieval_environment.database.session_factory.begin() as session:
        await session.execute(text("SET LOCAL enable_seqscan = off"))
        plan_rows = (
            await session.execute(
                text(
                    """EXPLAIN (COSTS OFF)
                    SELECT id
                    FROM document_chunks
                    WHERE to_tsvector(
                        'simple', coalesce(section_title, '') || ' ' || content
                    ) @@ websearch_to_tsquery('simple', 'VPN configuration')
                    """
                )
            )
        ).scalars()
        plan = "\n".join(plan_rows)

    assert "ix_document_chunks_fts" in plan


@pytest.mark.integration
async def test_role_restricted_document_is_filtered_before_retrieval(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "account_common_questions_faq.pdf",
        "Restricted Account FAQ",
    )
    async with retrieval_environment.database.session_factory.begin() as session:
        await session.execute(
            update(Document)
            .where(Document.id == imported.document_id)
            .values(visibility="role_restricted", allowed_roles=["helpdesk"])
        )

    employee_results = await retrieval_environment.retriever.search(
        "Restricted Account FAQ",
        top_k=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
    )
    helpdesk_results = await retrieval_environment.retriever.search(
        "Restricted Account FAQ",
        top_k=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="helpdesk"),
    )

    assert employee_results == ()
    assert helpdesk_results
    assert all(result.document_id == imported.document_id for result in helpdesk_results)


@pytest.mark.integration
async def test_document_source_status_and_effective_filters_apply_to_both_strategies(
    retrieval_environment: RetrievalEnvironment,
) -> None:
    imported = await _import_and_index(
        retrieval_environment,
        "vpn_configuration_sop.md",
        "Filtered VPN Guide",
    )

    wrong_type = await retrieval_environment.retriever.search(
        "Filtered VPN Guide",
        top_k=5,
        filters=SearchFilters(
            document_id=imported.document_id,
            source_type=DocumentSourceType.PDF,
        ),
        user_context=UserContext(role="employee"),
    )
    before_effective = await retrieval_environment.retriever.search(
        "Filtered VPN Guide",
        top_k=5,
        filters=SearchFilters(
            document_id=imported.document_id,
            effective_at=datetime.now(UTC) - timedelta(days=1),
        ),
        user_context=UserContext(role="employee"),
    )
    async with retrieval_environment.database.session_factory.begin() as session:
        await session.execute(
            update(Document)
            .where(Document.id == imported.document_id)
            .values(status=DocumentStatus.ARCHIVED.value)
        )
    default_status = await retrieval_environment.retriever.search(
        "Filtered VPN Guide",
        top_k=5,
        filters=SearchFilters(document_id=imported.document_id),
        user_context=UserContext(role="employee"),
    )
    archived_status = await retrieval_environment.retriever.search(
        "Filtered VPN Guide",
        top_k=5,
        filters=SearchFilters(
            document_id=imported.document_id,
            status=DocumentStatus.ARCHIVED,
        ),
        user_context=UserContext(role="employee"),
    )

    assert wrong_type == ()
    assert before_effective == ()
    assert default_status == ()
    assert archived_status


@pytest.mark.integration
async def test_retrieval_evaluation_cli_reports_recall_and_negative_abstention(
    retrieval_environment: RetrievalEnvironment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = Settings(environment=Environment.TEST).model_copy(
        update={
            "embedding_model": PROFILE.model,
            "embedding_dimension": PROFILE.dimension,
            "embedding_version": PROFILE.version,
        }
    )

    exit_code = await run_retrieval_evaluation(
        Namespace(
            dataset=Path("data/evaluation/retrieval_cases.json"),
            user_role="employee",
            seed_fixtures=True,
        ),
        settings=settings,
    )
    output = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert exit_code == 0
    assert output["total_cases"] == 18
    assert output["positive_cases"] == 15
    assert output["negative_cases"] == 3
    assert output["recall_at_3"] >= 0.8
    assert output["recall_at_5"] >= output["recall_at_3"]
    assert output["false_answer_rate"] == 0
    assert output["abstention_accuracy"] == 1
    assert len(output["missed_at_3"]) <= 3
    assert output["missed_at_5"] == []
