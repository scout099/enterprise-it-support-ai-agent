"""SQLAlchemy models owned by the Agent Runtime module."""

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enterprise_it_support.platform.database import Base


class AgentRun(Base):
    """One bounded graph execution with its latest recoverable state."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('running', 'waiting_approval', 'completed', 'needs_clarification', "
            "'escalated', 'failed')",
            name="ck_agent_runs_status",
        ),
        CheckConstraint(
            "intent_confidence >= 0 AND intent_confidence <= 1",
            name="ck_agent_runs_confidence",
        ),
        Index("ix_agent_runs_request_id", "request_id"),
        Index("ix_agent_runs_conversation_id", "conversation_id"),
        Index("ix_agent_runs_started_at", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(128))
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    intent: Mapped[str | None] = mapped_column(String(50))
    intent_confidence: Mapped[float] = mapped_column(default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20))
    current_node: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[dict[str, Any]] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.sequence_number",
    )


class AgentStep(Base):
    """One observable attempt to execute a named graph node."""

    __tablename__ = "agent_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence_number", name="uq_agent_steps_run_sequence"),
        CheckConstraint("sequence_number > 0", name="ck_agent_steps_positive_sequence"),
        CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_agent_steps_status",
        ),
        CheckConstraint("latency_ms >= 0", name="ck_agent_steps_nonnegative_latency"),
        Index("ix_agent_steps_run_started", "run_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    node_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run: Mapped[AgentRun] = relationship(back_populates="steps")
