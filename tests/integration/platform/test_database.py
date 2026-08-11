"""Real PostgreSQL and pgvector readiness test."""

import pytest
from alembic import command
from alembic.config import Config

from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


@pytest.mark.integration
async def test_migration_enables_database_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)

    try:
        result = await database.check()
    finally:
        await database.close()

    assert result.ready is True
    assert result.reason == "ok"
    get_settings.cache_clear()


@pytest.mark.integration
async def test_database_reports_connection_failure() -> None:
    database = DatabaseManager("postgresql+psycopg://user:password@127.0.0.1:1/unreachable")

    try:
        result = await database.check()
    finally:
        await database.close()

    assert result.ready is False
    assert result.reason == "connection_failed"


@pytest.mark.integration
async def test_database_reports_missing_vector_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    alembic_config = Config("alembic.ini")
    settings = Settings(environment=Environment.TEST)
    database: DatabaseManager | None = None

    command.downgrade(alembic_config, "base")
    try:
        database = DatabaseManager(settings.active_database_url)
        result = await database.check()
    finally:
        if database is not None:
            await database.close()
        command.upgrade(alembic_config, "head")
        get_settings.cache_clear()

    assert result.ready is False
    assert result.reason == "vector_extension_missing"
