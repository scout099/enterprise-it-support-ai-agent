"""Shared pytest fixtures."""

import pytest

from enterprise_it_support.platform.config import Environment, Settings


@pytest.fixture
def test_settings() -> Settings:
    """Return isolated settings that never read a developer's local .env file."""
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url="postgresql+psycopg://user:password@localhost:5432/app",
        test_database_url="postgresql+psycopg://user:password@localhost:5432/app_test",
        log_level="CRITICAL",
    )
