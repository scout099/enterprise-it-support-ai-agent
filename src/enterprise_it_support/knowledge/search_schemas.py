"""HTTP request and response schemas for Retrieval-only knowledge search."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from enterprise_it_support.knowledge.domain import DocumentSourceType, DocumentStatus
from enterprise_it_support.knowledge.retrieval import RetrievalMethod


class SearchFiltersRequest(BaseModel):
    """Allowlisted filters applied before keyword and vector ranking."""

    document_id: UUID | None = None
    source_type: DocumentSourceType | None = None
    status: DocumentStatus | None = None
    effective_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None


class KnowledgeSearchRequest(BaseModel):
    """Bounded hybrid-search request without any answer-generation controls."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: SearchFiltersRequest = Field(default_factory=SearchFiltersRequest)
    user_role: str = Field(min_length=1, max_length=100)

    @field_validator("query", "user_role")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class CitationResponse(BaseModel):
    """Stable source metadata for one result."""

    document_title: str
    document_version: int
    section_title: str | None
    chunk_id: UUID


class SearchResultResponse(BaseModel):
    """Ranked Chunk content plus complete citation information."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version: int
    content: str
    section_title: str | None
    score: float
    retrieval_method: RetrievalMethod
    citation: CitationResponse
