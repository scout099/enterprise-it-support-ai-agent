"""Transactional conversation persistence without exposing ORM models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.conversation.models import Conversation, Message
from enterprise_it_support.intelligence.model_gateway import TokenUsage


class ConversationNotFoundError(LookupError):
    """Raised when a requested conversation does not exist."""


class ConversationRoleMismatchError(PermissionError):
    """Raised when a caller attempts to continue a conversation under another role."""


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
        question: str,
        retrieval_query: str,
        retrieved_chunk_ids: tuple[UUID, ...],
        model_provider: str,
        configured_model: str,
        model_name: str,
        model_attempts: int,
        prompt_version: str,
        response: dict[str, Any],
        latency_ms: int,
        token_usage: TokenUsage,
        request_id: str,
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
                content=question,
                request_id=request_id,
            )
            assistant_message = Message(
                conversation_id=conversation.id,
                sequence_number=starting_sequence + 1,
                role="assistant",
                content=str(response["answer"]),
                retrieval_query=retrieval_query,
                retrieved_chunk_ids=list(retrieved_chunk_ids),
                model_provider=model_provider,
                configured_model=configured_model,
                model_name=model_name,
                model_attempts=model_attempts,
                prompt_version=prompt_version,
                response=response,
                latency_ms=latency_ms,
                input_tokens=token_usage.input_tokens,
                output_tokens=token_usage.output_tokens,
                total_tokens=token_usage.total_tokens,
                cached_tokens=token_usage.cached_tokens,
                reasoning_tokens=token_usage.reasoning_tokens,
                request_id=request_id,
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
