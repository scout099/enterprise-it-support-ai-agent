"""Transactional conversation persistence without exposing ORM models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.conversation.models import Conversation, Message
from enterprise_it_support.intelligence.model_gateway import ModelCallMetadata, TokenUsage


class ConversationNotFoundError(LookupError):
    """Raised when a requested conversation does not exist."""


class ConversationRoleMismatchError(PermissionError):
    """Raised when a caller attempts to continue a conversation under another role."""


class TurnStatus(StrEnum):
    """Persisted outcome of one accepted chat turn."""

    SUCCEEDED = "succeeded"
    REFUSED = "refused"
    FAILED = "failed"


class ErrorStage(StrEnum):
    """Safe stage taxonomy for failed grounded-answer attempts."""

    RETRIEVAL = "retrieval"
    MODEL = "model"
    VALIDATION = "validation"
    CITATION = "citation"


@dataclass(frozen=True)
class TurnTrace:
    """Complete observable outcome persisted independently from a successful answer."""

    question: str
    retrieval_query: str
    retrieved_chunk_ids: tuple[UUID, ...]
    model_metadata: ModelCallMetadata
    assistant_content: str
    response: dict[str, Any] | None
    latency_ms: int
    request_id: str
    status: TurnStatus
    error_stage: ErrorStage | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class StoredMessage:
    id: UUID
    sequence_number: int
    role: str
    content: str
    retrieval_query: str | None
    retrieved_chunk_ids: tuple[UUID, ...]
    model_provider: str | None
    configured_model: str | None
    model_name: str | None
    model_attempts: int
    prompt_version: str | None
    response: dict[str, Any] | None
    status: TurnStatus | None
    error_stage: ErrorStage | None
    error_code: str | None
    latency_ms: int | None
    token_usage: TokenUsage
    request_id: str
    created_at: datetime


@dataclass(frozen=True)
class StoredConversation:
    id: UUID
    user_role: str
    created_at: datetime
    updated_at: datetime
    messages: tuple[StoredMessage, ...]


@dataclass(frozen=True)
class SavedTurn:
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID


class ConversationRepository:
    """Create and read complete chat turns through one module-owned transaction."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_turn(
        self,
        *,
        conversation_id: UUID | None,
        user_role: str,
        trace: TurnTrace,
    ) -> SavedTurn:
        async with self._session_factory() as session, session.begin():
            if conversation_id is None:
                conversation = Conversation(user_role=user_role)
                session.add(conversation)
                await session.flush()
                starting_sequence = 1
            else:
                conversation = await session.scalar(
                    select(Conversation).where(Conversation.id == conversation_id).with_for_update()
                )
                if conversation is None:
                    raise ConversationNotFoundError(str(conversation_id))
                if conversation.user_role != user_role:
                    raise ConversationRoleMismatchError(str(conversation_id))
                latest_sequence = await session.scalar(
                    select(func.max(Message.sequence_number)).where(
                        Message.conversation_id == conversation.id
                    )
                )
                starting_sequence = int(latest_sequence or 0) + 1

            user_message = Message(
                conversation_id=conversation.id,
                sequence_number=starting_sequence,
                role="user",
                content=trace.question,
                request_id=trace.request_id,
            )
            assistant_message = Message(
                conversation_id=conversation.id,
                sequence_number=starting_sequence + 1,
                role="assistant",
                content=trace.assistant_content,
                retrieval_query=trace.retrieval_query,
                retrieved_chunk_ids=list(trace.retrieved_chunk_ids),
                model_provider=trace.model_metadata.provider,
                configured_model=trace.model_metadata.configured_model,
                model_name=trace.model_metadata.resolved_model,
                model_attempts=trace.model_metadata.attempts,
                prompt_version=trace.model_metadata.prompt_version,
                response=trace.response,
                status=trace.status.value,
                error_stage=(None if trace.error_stage is None else trace.error_stage.value),
                error_code=trace.error_code,
                latency_ms=trace.latency_ms,
                input_tokens=trace.model_metadata.usage.input_tokens,
                output_tokens=trace.model_metadata.usage.output_tokens,
                total_tokens=trace.model_metadata.usage.total_tokens,
                cached_tokens=trace.model_metadata.usage.cached_tokens,
                reasoning_tokens=trace.model_metadata.usage.reasoning_tokens,
                request_id=trace.request_id,
            )
            conversation.updated_at = datetime.now(UTC)
            session.add_all([user_message, assistant_message])
            await session.flush()
            return SavedTurn(
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message.id,
            )

    async def get(self, conversation_id: UUID) -> StoredConversation:
        async with self._session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(str(conversation_id))
            rows = (
                await session.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.sequence_number)
                )
            ).all()
            return StoredConversation(
                id=conversation.id,
                user_role=conversation.user_role,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=tuple(self._stored_message(row) for row in rows),
            )

    @staticmethod
    def _stored_message(message: Message) -> StoredMessage:
        return StoredMessage(
            id=message.id,
            sequence_number=message.sequence_number,
            role=message.role,
            content=message.content,
            retrieval_query=message.retrieval_query,
            retrieved_chunk_ids=tuple(message.retrieved_chunk_ids),
            model_provider=message.model_provider,
            configured_model=message.configured_model,
            model_name=message.model_name,
            model_attempts=message.model_attempts,
            prompt_version=message.prompt_version,
            response=message.response,
            status=(None if message.status is None else TurnStatus(message.status)),
            error_stage=(None if message.error_stage is None else ErrorStage(message.error_stage)),
            error_code=message.error_code,
            latency_ms=message.latency_ms,
            token_usage=TokenUsage(
                input_tokens=message.input_tokens,
                output_tokens=message.output_tokens,
                total_tokens=message.total_tokens,
                cached_tokens=message.cached_tokens,
                reasoning_tokens=message.reasoning_tokens,
            ),
            request_id=message.request_id,
            created_at=message.created_at,
        )
