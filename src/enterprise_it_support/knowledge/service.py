"""Application service for versioned knowledge document ingestion."""

from asyncio import to_thread
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.domain import (
    DocumentChunksView,
    DocumentSummaryView,
    DocumentView,
)
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository


class DocumentIngestionError(ValueError):
    """Base error for safe, user-correctable ingestion failures."""


class DocumentTooLargeError(DocumentIngestionError):
    """Raised before parsing when an upload exceeds its configured limit."""


class EmptyDocumentError(DocumentIngestionError):
    """Raised when parsing or chunking produces no useful content."""


class DocumentNotFoundError(LookupError):
    """Raised when a requested logical document does not exist."""


@dataclass(frozen=True)
class DocumentImportResult:
    """Observable result of a versioned document import."""

    document_id: UUID
    document_version_id: UUID
    version: int
    chunk_count: int
    created_version: bool


class LocalDocumentStorage:
    """Store raw uploads under generated names inside one configured root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, filename: str, data: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        relative_path = Path("raw") / f"{uuid4().hex}{suffix}"
        target = self._root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return relative_path.as_posix()

    def delete(self, relative_path: str) -> None:
        target = self._root / relative_path
        if target.is_file():
            target.unlink()


class DocumentIngestionService:
    """Coordinate validation, parsing, hashing, chunking, storage, and persistence."""

    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        parser_registry: DocumentParserRegistry,
        chunker: DocumentChunker,
        storage: LocalDocumentStorage,
        max_file_size_bytes: int,
    ) -> None:
        self._repository = repository
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._storage = storage
        self._max_file_size_bytes = max_file_size_bytes

    async def ingest(
        self,
        *,
        filename: str,
        data: bytes,
        owner: str,
        source_name: str,
        title: str | None = None,
        source_description: str | None = None,
        effective_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> DocumentImportResult:
        """Import one file, reusing an identical version when present."""
        if not data:
            raise EmptyDocumentError("Uploaded document is empty")
        if len(data) > self._max_file_size_bytes:
            raise DocumentTooLargeError("Uploaded document exceeds the configured size limit")

        parsed = await to_thread(self._parser_registry.parse, filename, data)
        resolved_title = (title or parsed.title).strip()
        resolved_owner = owner.strip()
        resolved_source_name = source_name.strip()
        if not resolved_title or not resolved_owner or not resolved_source_name:
            raise DocumentIngestionError("Title, owner, and source name cannot be blank")
        if len(resolved_title) > 500:
            raise DocumentIngestionError("Title cannot exceed 500 characters")
        content_hash = sha256(parsed.canonical_text.encode("utf-8")).hexdigest()

        duplicate = await self._repository.find_duplicate(
            source_name=resolved_source_name,
            title=resolved_title,
            content_hash=content_hash,
        )
        if duplicate is not None:
            return DocumentImportResult(**duplicate.__dict__)

        chunks = await to_thread(self._chunker.split, parsed)
        if not chunks:
            raise EmptyDocumentError("Document did not produce meaningful chunks")
        raw_file_path = await to_thread(self._storage.save, filename, data)

        try:
            persisted = await self._repository.persist_import(
                source_name=resolved_source_name,
                source_description=source_description,
                title=resolved_title,
                source_type=parsed.source_type,
                owner=resolved_owner,
                content_hash=content_hash,
                effective_at=effective_at or datetime.now(UTC),
                expires_at=expires_at,
                raw_file_path=raw_file_path,
                chunks=chunks,
            )
        except Exception:
            await to_thread(self._storage.delete, raw_file_path)
            raise

        if not persisted.created_version:
            await to_thread(self._storage.delete, raw_file_path)
        return DocumentImportResult(**persisted.__dict__)

    async def get_document(self, document_id: UUID) -> DocumentView:
        """Return one document with all immutable version summaries."""
        document = await self._repository.get_document(document_id)
        if document is None:
            raise DocumentNotFoundError("Knowledge document was not found")
        return document

    async def list_documents(self) -> tuple[DocumentSummaryView, ...]:
        """List logical knowledge documents without loading chunk content."""
        return await self._repository.list_documents()

    async def get_latest_chunks(self, document_id: UUID) -> DocumentChunksView:
        """Return traceable chunks from the newest retained version."""
        chunks = await self._repository.get_latest_chunks(document_id)
        if chunks is None:
            raise DocumentNotFoundError("Knowledge document was not found")
        return chunks
