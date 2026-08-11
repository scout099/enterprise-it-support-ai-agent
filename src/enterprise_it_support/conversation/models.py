"""SQLAlchemy models owned by the conversation module."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enterprise_it_support.platform.database import Base


class Conversation(Base):
    """Stable multi-turn chat identity with one fixed authorization role."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_updated_at", "updated_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_role: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sequence_number",
    )


class Message(Base):
    """One persisted user or assistant message plus optional RAG trace."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_sequence",
        ),
        CheckConstraint("sequence_number > 0", name="ck_messages_positive_sequence"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_messages_nonnegative_latency",
        ),
        CheckConstraint(
            "model_attempts >= 0 AND input_tokens >= 0 AND output_tokens >= 0 "
            "AND total_tokens >= 0 AND cached_tokens >= 0 AND reasoning_tokens >= 0",
            name="ck_messages_nonnegative_tokens",
        ),
        CheckConstraint(
            "status IS NULL OR status IN ('succeeded', 'refused', 'failed')",
            name="ck_messages_status",
        ),
        CheckConstraint(
            "error_stage IS NULL OR error_stage IN "
            "('retrieval', 'model', 'validation', 'citation')",
            name="ck_messages_error_stage",
        ),
        CheckConstraint(
            "(role = 'user' AND status IS NULL AND error_stage IS NULL "
            "AND error_code IS NULL AND response IS NULL) OR "
            "(role = 'assistant' AND status IN ('succeeded', 'refused') "
            "AND error_stage IS NULL AND error_code IS NULL AND response IS NOT NULL) OR "
            "(role = 'assistant' AND status = 'failed' AND error_stage IS NOT NULL "
            "AND error_code IS NOT NULL AND response IS NULL)",
            name="ck_messages_trace_outcome",
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_request_id", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    retrieval_query: Mapped[str | None] = mapped_column(Text)
    retrieved_chunk_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid),
        default=list,
        server_default="{}",
    )
    model_provider: Mapped[str | None] = mapped_column(String(100))
    configured_model: Mapped[str | None] = mapped_column(String(200))
    model_name: Mapped[str | None] = mapped_column(String(200))
    model_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    status: Mapped[str | None] = mapped_column(String(20))
    error_stage: Mapped[str | None] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(100))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    request_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
