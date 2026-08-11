"""Versioned knowledge ingestion tests against PostgreSQL."""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.knowledge.service import DocumentIngestionService, LocalDocumentStorage
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

FIXTURES = Path(__file__).parents[2] / "fixtures" / "knowledge"


@pytest.fixture
async def ingestion_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> DocumentIngestionService:
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
    service = DocumentIngestionService(
        repository=KnowledgeRepository(database.session_factory),
        parser_registry=DocumentParserRegistry(),
        chunker=DocumentChunker(chunk_size=40, chunk_overlap=5),
        storage=LocalDocumentStorage(tmp_path),
        max_file_size_bytes=1_000_000,
    )

    yield service

    await database.close()
    get_settings.cache_clear()


@pytest.mark.integration
async def test_duplicate_content_reuses_existing_document_version(
    ingestion_service: DocumentIngestionService,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    data = path.read_bytes()

    first = await ingestion_service.ingest(
        filename=path.name,
        data=data,
        title="VPN Configuration SOP",
        owner="Demo IT Operations",
        source_name="Local SOP Library",
    )
    duplicate = await ingestion_service.ingest(
        filename=path.name,
        data=data,
        title="VPN Configuration SOP",
        owner="Demo IT Operations",
        source_name="Local SOP Library",
    )

    assert first.created_version is True
    assert duplicate.created_version is False
    assert duplicate.document_id == first.document_id
    assert duplicate.document_version_id == first.document_version_id
    assert duplicate.version == 1
    assert duplicate.chunk_count == first.chunk_count


@pytest.mark.integration
async def test_changed_content_creates_new_version_and_keeps_history(
    ingestion_service: DocumentIngestionService,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    original_data = path.read_bytes()
    changed_data = original_data.replace(
        b"Escalate after three failed attempts.",
        b"Escalate after two failed attempts and record the fictional error code.",
    )

    first = await ingestion_service.ingest(
        filename=path.name,
        data=original_data,
        title="VPN Configuration SOP",
        owner="Demo IT Operations",
        source_name="Local SOP Library",
    )
    second = await ingestion_service.ingest(
        filename=path.name,
        data=changed_data,
        title="VPN Configuration SOP",
        owner="Demo IT Operations",
        source_name="Local SOP Library",
    )
    document = await ingestion_service.get_document(first.document_id)

    assert second.created_version is True
    assert second.document_id == first.document_id
    assert second.document_version_id != first.document_version_id
    assert second.version == 2
    assert [version.version for version in document.versions] == [1, 2]
    assert document.versions[0].content_hash != document.versions[1].content_hash


@pytest.mark.integration
async def test_concurrent_first_import_reuses_one_document_version(
    ingestion_service: DocumentIngestionService,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    import_arguments = {
        "filename": path.name,
        "data": path.read_bytes(),
        "title": "Concurrent VPN Configuration SOP",
        "owner": "Demo IT Operations",
        "source_name": "Concurrent Local SOP Library",
    }

    first, second = await asyncio.gather(
        ingestion_service.ingest(**import_arguments),
        ingestion_service.ingest(**import_arguments),
    )

    assert first.document_id == second.document_id
    assert first.document_version_id == second.document_version_id
    assert first.version == second.version == 1
    assert sorted([first.created_version, second.created_version]) == [False, True]
