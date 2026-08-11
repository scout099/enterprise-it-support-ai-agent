"""SQLAlchemy database lifecycle and readiness checks."""

import logging
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base reserved for later domain models."""


@dataclass(frozen=True)
class DatabaseCheckResult:
    """Observable result returned by the database readiness interface."""

    ready: bool
    reason: str


class DatabaseLifecycle(Protocol):
    """Small database interface required by the HTTP application."""

    async def check(self) -> DatabaseCheckResult: ...

    async def close(self) -> None: ...


class DatabaseManager:
    """Own the async SQLAlchemy engine and database readiness behavior."""

    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3},
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the session factory used by module-owned repositories."""
        return self._session_factory

    async def check(self) -> DatabaseCheckResult:
        """Verify connectivity and that the vector extension is enabled."""
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                vector_enabled = await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                )
        except SQLAlchemyError as exception:
            logger.warning(
                "database_readiness_check_failed error_type=%s",
                type(exception).__name__,
            )
            return DatabaseCheckResult(ready=False, reason="connection_failed")

        if vector_enabled is not True:
            return DatabaseCheckResult(ready=False, reason="vector_extension_missing")
        return DatabaseCheckResult(ready=True, reason="ok")

    async def close(self) -> None:
        """Release pooled connections during application shutdown."""
        await self._engine.dispose()
