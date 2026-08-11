"""Format-independent knowledge ingestion domain objects."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class DocumentSourceType(StrEnum):
    """File formats accepted by the MVP ingestion boundary."""

    MARKDOWN = "markdown"
    TXT = "txt"
    PDF = "pdf"


class DocumentStatus(StrEnum):
    """Lifecycle state of a logical knowledge document."""

    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class SourceLocation:
    """Location of parsed text in its original source."""

    start_line: int | None = None
    end_line: int | None = None
    page_number: int | None = None


@dataclass(frozen=True)
class DocumentSection:
    """A normalized block of document text and its source position."""

    content: str
    location: SourceLocation
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentContent:
    """Format-independent parser output consumed by chunking and ingestion."""

    source_type: DocumentSourceType
    title: str
    sections: tuple[DocumentSection, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def canonical_text(self) -> str:
        """Return stable normalized text used for content hashing."""
        normalized_sections = []
        for section in self.sections:
            parts = [part for part in (section.title, section.content.strip()) if part]
            normalized_sections.append("\n".join(parts))
        return "\n\n".join(normalized_sections).strip()


@dataclass(frozen=True)
class DocumentVersionView:
    """Immutable version data returned by the knowledge application boundary."""

    id: UUID
    version: int
    content_hash: str
    effective_at: datetime
    expires_at: datetime | None
    raw_file_path: str
    created_at: datetime


@dataclass(frozen=True)
class DocumentView:
    """Logical document details with all retained versions."""

    id: UUID
    knowledge_source_id: UUID
    source_name: str
    title: str
    source_type: DocumentSourceType
    status: DocumentStatus
    owner: str
    created_at: datetime
    updated_at: datetime
    versions: tuple[DocumentVersionView, ...]


@dataclass(frozen=True)
class DocumentSummaryView:
    """List projection for a logical knowledge document."""

    id: UUID
    source_name: str
    title: str
    source_type: DocumentSourceType
    status: DocumentStatus
    owner: str
    latest_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DocumentChunkView:
    """Persisted chunk projection with its immutable version identity."""

    id: UUID
    document_version_id: UUID
    chunk_index: int
    content: str
    token_count: int
    section_title: str | None
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class DocumentChunksView:
    """Latest-version chunks returned for one logical document."""

    document_id: UUID
    document_version_id: UUID
    version: int
    chunks: tuple[DocumentChunkView, ...]
