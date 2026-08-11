"""HTTP schemas for Chunk embedding indexing."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IndexDocumentRequest(BaseModel):
    """Optional controls for a document indexing request."""

    force: bool = False


class IndexDocumentResponse(BaseModel):
    """Batch-level aggregate returned after an indexing attempt."""

    document_id: UUID
    indexed_chunks: int
    skipped_chunks: int
    failed_chunks: int
    successful_batches: int
    failed_batches: int
    model: str
    version: str
    dimension: int


class IndexStatusResponse(BaseModel):
    """Current configured Embedding Profile coverage."""

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
