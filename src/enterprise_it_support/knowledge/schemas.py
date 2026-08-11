"""Public HTTP schemas for knowledge document ingestion and reads."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from enterprise_it_support.knowledge.domain import DocumentSourceType, DocumentStatus


class DocumentImportResponse(BaseModel):
    """Result of importing or deduplicating one document version."""

    document_id: UUID
    document_version_id: UUID
    version: int
    chunk_count: int
    created_version: bool


class DocumentSummaryResponse(BaseModel):
    """Document list item."""

    id: UUID
    source_name: str
    title: str
    source_type: DocumentSourceType
    status: DocumentStatus
    owner: str
    latest_version: int
    created_at: datetime
    updated_at: datetime


class DocumentVersionResponse(BaseModel):
    """Safe immutable version metadata returned without internal file paths."""

    id: UUID
    version: int
    content_hash: str
    effective_at: datetime
    expires_at: datetime | None
    created_at: datetime


class DocumentDetailResponse(BaseModel):
    """Logical document and all retained version summaries."""

    id: UUID
    knowledge_source_id: UUID
    source_name: str
    title: str
    source_type: DocumentSourceType
    status: DocumentStatus
    owner: str
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse]


class DocumentChunkResponse(BaseModel):
    """Traceable chunk from one immutable document version."""

    id: UUID
    document_version_id: UUID
    chunk_index: int
    content: str
    token_count: int
    section_title: str | None
    metadata: dict[str, Any]
    created_at: datetime


class DocumentChunksResponse(BaseModel):
    """Latest version and its ordered chunks."""

    document_id: UUID
    document_version_id: UUID
    version: int
    chunks: list[DocumentChunkResponse]
