"""Knowledge schema migration tests against PostgreSQL."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from enterprise_it_support.platform.config import Environment, Settings, get_settings

EXPECTED_COLUMNS = {
    "conversations": {"id", "user_role", "created_at", "updated_at"},
    "messages": {
        "id",
        "conversation_id",
        "sequence_number",
        "role",
        "content",
        "retrieval_query",
        "retrieved_chunk_ids",
        "model_provider",
        "configured_model",
        "model_name",
        "model_attempts",
        "prompt_version",
        "response",
        "status",
        "error_stage",
        "error_code",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_tokens",
        "reasoning_tokens",
        "request_id",
        "created_at",
    },
    "knowledge_sources": {"id", "name", "description", "created_at", "updated_at"},
    "documents": {
        "id",
        "knowledge_source_id",
        "title",
        "source_type",
        "status",
        "visibility",
        "allowed_roles",
        "owner",
        "created_at",
        "updated_at",
    },
    "document_versions": {
        "id",
        "document_id",
        "version",
        "content_hash",
        "effective_at",
        "expires_at",
        "raw_file_path",
        "created_at",
    },
    "document_chunks": {
        "id",
        "document_version_id",
        "chunk_index",
        "content",
        "token_count",
        "section_title",
        "metadata",
        "embedding",
        "embedding_model",
        "embedding_version",
        "indexed_at",
        "created_at",
    },
}


@pytest.mark.integration
async def test_knowledge_migration_creates_required_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    engine = create_async_engine(settings.active_database_url)

    try:
        async with engine.connect() as connection:
            table_columns = await connection.run_sync(
                lambda sync_connection: {
                    table_name: {
                        column["name"]
                        for column in inspect(sync_connection).get_columns(table_name)
                    }
                    for table_name in EXPECTED_COLUMNS
                }
            )
            index_names = set(
                (
                    await connection.execute(
                        text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
                    )
                ).scalars()
            )
    finally:
        await engine.dispose()
        get_settings.cache_clear()

    assert table_columns == EXPECTED_COLUMNS
    assert "ix_document_chunks_fts" in index_names
