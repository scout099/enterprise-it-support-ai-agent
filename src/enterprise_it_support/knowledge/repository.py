"""PostgreSQL repository for the knowledge module."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.knowledge.chunking import DocumentChunkDraft
from enterprise_it_support.knowledge.domain import (
    DocumentChunksView,
    DocumentChunkView,
    DocumentSourceType,
    DocumentStatus,
    DocumentSummaryView,
    DocumentVersionView,
    DocumentView,
)
from enterprise_it_support.knowledge.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    KnowledgeSource,
)


class DocumentSourceTypeConflictError(ValueError):
    """Raised when a logical Document is uploaded using another file type."""


@dataclass(frozen=True)
class PersistedImport:
    """Identifiers and status returned after an atomic import attempt."""

    document_id: UUID
    document_version_id: UUID
    version: int
    chunk_count: int
    created_version: bool


class KnowledgeRepository:
    """Own knowledge persistence queries and transaction boundaries."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def find_duplicate(
        self,
        *,
        source_name: str,
        title: str,
        content_hash: str,
    ) -> PersistedImport | None:
        """Return an existing version with the same normalized content."""
        async with self._session_factory() as session:
            statement = (
                select(
                    Document.id,
                    DocumentVersion.id,
                    DocumentVersion.version,
                    func.count(DocumentChunk.id),
                )
                .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
                .join(DocumentVersion, DocumentVersion.document_id == Document.id)
                .outerjoin(DocumentChunk, DocumentChunk.document_version_id == DocumentVersion.id)
                .where(
                    KnowledgeSource.name == source_name,
                    Document.title == title,
                    DocumentVersion.content_hash == content_hash,
                )
                .group_by(Document.id, DocumentVersion.id, DocumentVersion.version)
            )
            row = (await session.execute(statement)).one_or_none()
            if row is None:
                return None
            return PersistedImport(
                document_id=row[0],
                document_version_id=row[1],
                version=row[2],
                chunk_count=row[3],
                created_version=False,
            )

    async def get_document(self, document_id: UUID) -> DocumentView | None:
        """Return one logical document and every retained version."""
        async with self._session_factory() as session:
            document_row = (
                await session.execute(
                    select(Document, KnowledgeSource.name)
                    .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
                    .where(Document.id == document_id)
                )
            ).one_or_none()
            if document_row is None:
                return None
            document, source_name = document_row
            versions = (
                await session.scalars(
                    select(DocumentVersion)
                    .where(DocumentVersion.document_id == document_id)
                    .order_by(DocumentVersion.version)
                )
            ).all()
            return DocumentView(
                id=document.id,
                knowledge_source_id=document.knowledge_source_id,
                source_name=source_name,
                title=document.title,
                source_type=DocumentSourceType(document.source_type),
                status=DocumentStatus(document.status),
                owner=document.owner,
                created_at=document.created_at,
                updated_at=document.updated_at,
                versions=tuple(
                    DocumentVersionView(
                        id=version.id,
                        version=version.version,
                        content_hash=version.content_hash,
                        effective_at=version.effective_at,
                        expires_at=version.expires_at,
                        raw_file_path=version.raw_file_path,
                        created_at=version.created_at,
                    )
                    for version in versions
                ),
            )

    async def list_documents(self) -> tuple[DocumentSummaryView, ...]:
        """Return all logical documents with their latest version number."""
        latest_versions = (
            select(
                DocumentVersion.document_id,
                func.max(DocumentVersion.version).label("latest_version"),
            )
            .group_by(DocumentVersion.document_id)
            .subquery()
        )
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(Document, KnowledgeSource.name, latest_versions.c.latest_version)
                    .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
                    .join(latest_versions, latest_versions.c.document_id == Document.id)
                    .order_by(Document.created_at, Document.id)
                )
            ).all()
            return tuple(
                DocumentSummaryView(
                    id=document.id,
                    source_name=source_name,
                    title=document.title,
                    source_type=DocumentSourceType(document.source_type),
                    status=DocumentStatus(document.status),
                    owner=document.owner,
                    latest_version=latest_version,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                )
                for document, source_name, latest_version in rows
            )

    async def get_latest_chunks(self, document_id: UUID) -> DocumentChunksView | None:
        """Return chunks from the newest retained version of a Document."""
        async with self._session_factory() as session:
            version = await session.scalar(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.version.desc())
                .limit(1)
            )
            if version is None:
                return None
            chunks = (
                await session.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_version_id == version.id)
                    .order_by(DocumentChunk.chunk_index)
                )
            ).all()
            return DocumentChunksView(
                document_id=document_id,
                document_version_id=version.id,
                version=version.version,
                chunks=tuple(
                    DocumentChunkView(
                        id=chunk.id,
                        document_version_id=chunk.document_version_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        section_title=chunk.section_title,
                        metadata=chunk.metadata_,
                        created_at=chunk.created_at,
                    )
                    for chunk in chunks
                ),
            )

    async def persist_import(
        self,
        *,
        source_name: str,
        source_description: str | None,
        title: str,
        source_type: DocumentSourceType,
        owner: str,
        content_hash: str,
        effective_at: datetime,
        expires_at: datetime | None,
        raw_file_path: str,
        chunks: tuple[DocumentChunkDraft, ...],
    ) -> PersistedImport:
        """Create a new immutable version and its chunks in one transaction."""
        async with self._session_factory.begin() as session:
            document_key = f"{len(source_name)}:{source_name}{title}"
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:document_key, 0))"),
                {"document_key": document_key},
            )
            source = await session.scalar(
                select(KnowledgeSource).where(KnowledgeSource.name == source_name)
            )
            if source is None:
                source = KnowledgeSource(name=source_name, description=source_description)
                session.add(source)
                await session.flush()

            document = await session.scalar(
                select(Document)
                .where(
                    Document.knowledge_source_id == source.id,
                    Document.title == title,
                )
                .with_for_update()
            )
            if document is None:
                document = Document(
                    knowledge_source_id=source.id,
                    title=title,
                    source_type=source_type.value,
                    status=DocumentStatus.ACTIVE.value,
                    owner=owner,
                )
                session.add(document)
                await session.flush()
            elif document.source_type != source_type.value:
                raise DocumentSourceTypeConflictError(
                    "An existing document cannot change its source type"
                )

            duplicate = await self._find_duplicate_in_session(
                session,
                document_id=document.id,
                content_hash=content_hash,
            )
            if duplicate is not None:
                return duplicate

            latest_version = await session.scalar(
                select(func.max(DocumentVersion.version)).where(
                    DocumentVersion.document_id == document.id
                )
            )
            next_version = (latest_version or 0) + 1
            version = DocumentVersion(
                document_id=document.id,
                version=next_version,
                content_hash=content_hash,
                effective_at=effective_at,
                expires_at=expires_at,
                raw_file_path=raw_file_path,
            )
            session.add(version)
            await session.flush()
            session.add_all(
                [
                    DocumentChunk(
                        document_version_id=version.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        section_title=chunk.section_title,
                        metadata_=chunk.metadata,
                    )
                    for chunk in chunks
                ]
            )
            document.owner = owner
            document.updated_at = func.now()
            await session.flush()

            return PersistedImport(
                document_id=document.id,
                document_version_id=version.id,
                version=next_version,
                chunk_count=len(chunks),
                created_version=True,
            )

    async def _find_duplicate_in_session(
        self,
        session: AsyncSession,
        *,
        document_id: UUID,
        content_hash: str,
    ) -> PersistedImport | None:
        statement = (
            select(
                DocumentVersion.id,
                DocumentVersion.version,
                func.count(DocumentChunk.id),
            )
            .outerjoin(DocumentChunk, DocumentChunk.document_version_id == DocumentVersion.id)
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.content_hash == content_hash,
            )
            .group_by(DocumentVersion.id, DocumentVersion.version)
        )
        row = (await session.execute(statement)).one_or_none()
        if row is None:
            return None
        return PersistedImport(
            document_id=document_id,
            document_version_id=row[0],
            version=row[1],
            chunk_count=row[2],
            created_version=False,
        )
