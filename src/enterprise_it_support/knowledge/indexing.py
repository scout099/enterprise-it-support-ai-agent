"""Batch indexing application service and PostgreSQL persistence."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from uuid import UUID

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from enterprise_it_support.intelligence.embeddings import EmbeddingProvider
from enterprise_it_support.knowledge.models import Document, DocumentChunk, DocumentVersion

logger = logging.getLogger(__name__)


class IndexingDocumentNotFoundError(LookupError):
    """Raised when indexing targets an unknown logical Document."""


class EmbeddingValidationError(ValueError):
    """Raised when a provider response is incompatible with its profile."""


@dataclass(frozen=True)
class EmbeddingProfile:
    """Configuration that identifies one compatible embedding space."""

    model: str
    dimension: int
    version: str


@dataclass(frozen=True)
class ChunkForIndexing:
    """Minimal immutable Chunk data sent to an Embedding Provider."""

    id: UUID
    content: str


@dataclass(frozen=True)
class EmbeddingWrite:
    """Validated vector ready for one batch transaction."""

    chunk_id: UUID
    embedding: list[float]


@dataclass(frozen=True)
class IndexingResult:
    """Observable outcome of one document indexing request."""

    document_id: UUID
    indexed_chunks: int
    skipped_chunks: int
    failed_chunks: int
    successful_batches: int
    failed_batches: int
    model: str
    version: str
    dimension: int


@dataclass(frozen=True)
class IndexStatus:
    """Current Profile coverage for one logical Document."""

    document_id: UUID
    total_chunks: int
    indexed_chunks: int
    pending_chunks: int
    stale_chunks: int
    status: str
    model: str
    version: str
    dimension: int
    last_indexed_at: datetime | None


class IndexingRepository:
    """Own Chunk selection, profile status, and per-batch vector writes."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_candidates(
        self,
        document_id: UUID,
        profile: EmbeddingProfile,
        *,
        force: bool,
    ) -> tuple[ChunkForIndexing, ...] | None:
        """Return Chunks that need the requested Profile, or None if Document is absent."""
        async with self._session_factory() as session:
            exists = await session.scalar(select(Document.id).where(Document.id == document_id))
            if exists is None:
                return None

            statement = (
                select(DocumentChunk.id, DocumentChunk.content)
                .join(
                    DocumentVersion,
                    DocumentChunk.document_version_id == DocumentVersion.id,
                )
                .where(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.version, DocumentChunk.chunk_index)
            )
            if not force:
                statement = statement.where(not_(self._matches_profile(profile)))
            rows = (await session.execute(statement)).all()
            return tuple(ChunkForIndexing(id=row[0], content=row[1]) for row in rows)

    async def save_batch(
        self,
        writes: tuple[EmbeddingWrite, ...],
        profile: EmbeddingProfile,
    ) -> None:
        """Commit one validated provider batch independently."""
        if not writes:
            return
        indexed_at = datetime.now(UTC)
        chunk_ids = [write.chunk_id for write in writes]
        async with self._session_factory.begin() as session:
            chunks = (
                await session.scalars(
                    select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)).with_for_update()
                )
            ).all()
            chunks_by_id = {chunk.id: chunk for chunk in chunks}
            if len(chunks_by_id) != len(writes):
                raise RuntimeError("One or more document chunks disappeared during indexing")
            for write in writes:
                chunk = chunks_by_id[write.chunk_id]
                chunk.embedding = write.embedding
                chunk.embedding_model = profile.model
                chunk.embedding_version = profile.version
                chunk.indexed_at = indexed_at

    async def get_status(
        self,
        document_id: UUID,
        profile: EmbeddingProfile,
    ) -> IndexStatus | None:
        """Count current, pending, and stale Chunk embeddings for one Document."""
        async with self._session_factory() as session:
            exists = await session.scalar(select(Document.id).where(Document.id == document_id))
            if exists is None:
                return None

            current = self._matches_profile(profile)
            stale = and_(DocumentChunk.embedding.is_not(None), not_(current))
            row = (
                await session.execute(
                    select(
                        func.count(DocumentChunk.id),
                        func.count(DocumentChunk.id).filter(current),
                        func.count(DocumentChunk.id).filter(DocumentChunk.embedding.is_(None)),
                        func.count(DocumentChunk.id).filter(stale),
                        func.max(DocumentChunk.indexed_at),
                    )
                    .join(
                        DocumentVersion,
                        DocumentChunk.document_version_id == DocumentVersion.id,
                    )
                    .where(DocumentVersion.document_id == document_id)
                )
            ).one()
            total, indexed, pending, stale_count, last_indexed_at = row
            return IndexStatus(
                document_id=document_id,
                total_chunks=total,
                indexed_chunks=indexed,
                pending_chunks=pending,
                stale_chunks=stale_count,
                status=self._status_name(total, indexed, pending, stale_count),
                model=profile.model,
                version=profile.version,
                dimension=profile.dimension,
                last_indexed_at=last_indexed_at,
            )

    async def list_documents_requiring_index(
        self,
        profile: EmbeddingProfile,
    ) -> tuple[UUID, ...]:
        """Return logical Documents with at least one non-current Chunk."""
        async with self._session_factory() as session:
            document_ids = (
                await session.scalars(
                    select(DocumentVersion.document_id)
                    .join(
                        DocumentChunk,
                        DocumentChunk.document_version_id == DocumentVersion.id,
                    )
                    .where(not_(self._matches_profile(profile)))
                    .distinct()
                    .order_by(DocumentVersion.document_id)
                )
            ).all()
            return tuple(document_ids)

    @staticmethod
    def _matches_profile(profile: EmbeddingProfile) -> ColumnElement[bool]:
        return and_(
            DocumentChunk.embedding.is_not(None),
            DocumentChunk.embedding_model == profile.model,
            DocumentChunk.embedding_version == profile.version,
            func.vector_dims(DocumentChunk.embedding) == profile.dimension,
        )

    @staticmethod
    def _status_name(total: int, indexed: int, pending: int, stale: int) -> str:
        if total > 0 and indexed == total:
            return "indexed"
        if indexed > 0:
            return "partial"
        if stale > 0:
            return "stale"
        if pending > 0:
            return "pending"
        return "empty"


class IndexingService:
    """Generate and persist Chunk embeddings in independently committed batches."""

    def __init__(
        self,
        *,
        repository: IndexingRepository,
        provider: EmbeddingProvider,
        profile: EmbeddingProfile,
        batch_size: int,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Indexing batch size must be positive")
        if profile.dimension < 1:
            raise ValueError("Embedding dimension must be positive")
        self._repository = repository
        self._provider = provider
        self._profile = profile
        self._batch_size = batch_size

    async def index_document(self, document_id: UUID, *, force: bool = False) -> IndexingResult:
        """Index one Document, continuing after isolated batch failures."""
        candidates = await self._repository.get_candidates(
            document_id,
            self._profile,
            force=force,
        )
        if candidates is None:
            raise IndexingDocumentNotFoundError("Knowledge document was not found")
        status_before = await self._repository.get_status(document_id, self._profile)
        assert status_before is not None

        indexed_chunks = 0
        failed_chunks = 0
        successful_batches = 0
        failed_batches = 0
        for batch_start in range(0, len(candidates), self._batch_size):
            batch = candidates[batch_start : batch_start + self._batch_size]
            try:
                raw_embeddings = await self._provider.embed_documents(
                    [chunk.content for chunk in batch]
                )
                writes = self._validate_batch(batch, raw_embeddings)
                await self._repository.save_batch(writes, self._profile)
            except Exception as exception:
                failed_chunks += len(batch)
                failed_batches += 1
                logger.error(
                    "embedding_batch_failed document_id=%s batch_start=%d "
                    "batch_size=%d error_type=%s",
                    document_id,
                    batch_start,
                    len(batch),
                    type(exception).__name__,
                )
                continue
            indexed_chunks += len(batch)
            successful_batches += 1

        return IndexingResult(
            document_id=document_id,
            indexed_chunks=indexed_chunks,
            skipped_chunks=status_before.total_chunks - len(candidates),
            failed_chunks=failed_chunks,
            successful_batches=successful_batches,
            failed_batches=failed_batches,
            model=self._profile.model,
            version=self._profile.version,
            dimension=self._profile.dimension,
        )

    async def index_pending_documents(self) -> tuple[IndexingResult, ...]:
        """Index every Document with non-current Chunks."""
        document_ids = await self._repository.list_documents_requiring_index(self._profile)
        results = []
        for document_id in document_ids:
            results.append(await self.index_document(document_id))
        return tuple(results)

    async def get_status(self, document_id: UUID) -> IndexStatus:
        """Return current configured Profile coverage for one Document."""
        status = await self._repository.get_status(document_id, self._profile)
        if status is None:
            raise IndexingDocumentNotFoundError("Knowledge document was not found")
        return status

    def _validate_batch(
        self,
        chunks: tuple[ChunkForIndexing, ...],
        embeddings: list[list[float]],
    ) -> tuple[EmbeddingWrite, ...]:
        if len(embeddings) != len(chunks):
            raise EmbeddingValidationError(
                "Embedding provider returned a different number of vectors than inputs"
            )
        writes = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if len(embedding) != self._profile.dimension:
                raise EmbeddingValidationError(
                    "Embedding provider returned an unexpected vector dimension"
                )
            vector = [float(value) for value in embedding]
            if not all(isfinite(value) for value in vector):
                raise EmbeddingValidationError("Embedding vector contains a non-finite value")
            if not any(value != 0.0 for value in vector):
                raise EmbeddingValidationError("Embedding vector cannot be a zero vector")
            writes.append(EmbeddingWrite(chunk_id=chunk.id, embedding=vector))
        return tuple(writes)
