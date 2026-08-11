"""HTTP schemas for grounded chat and persisted conversations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from enterprise_it_support.agent_runtime.rag import AnswerCitation, RAGAnswer


class ChatAskRequest(BaseModel):
    """Bounded request for a new or continuing grounded chat turn."""

    question: str = Field(min_length=1, max_length=2000)
    user_role: str = Field(min_length=1, max_length=100)
    conversation_id: UUID | None = None

    @field_validator("question", "user_role")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class TokenUsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0


class ChatAskResponse(BaseModel):
    """Grounded answer plus IDs and model-call trace metadata."""

    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    summary: str
    answer: str
    diagnosis: list[str]
    citations: list[AnswerCitation]
    limitations: list[str]
    next_steps: list[str]
    confidence: float
    model_name: str
    model_provider: str
    configured_model: str
    model_attempts: int
    prompt_version: str
    token_usage: TokenUsageResponse
    latency_ms: int
    request_id: str


class ConversationMessageResponse(BaseModel):
    id: UUID
    sequence_number: int
    role: str
    content: str
    retrieval_query: str | None
    retrieved_chunk_ids: list[UUID]
    model_name: str | None
    model_provider: str | None
    configured_model: str | None
    model_attempts: int
    prompt_version: str | None
    response: RAGAnswer | dict[str, Any] | None
    latency_ms: int | None
    token_usage: TokenUsageResponse
    request_id: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: UUID
    user_role: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]
