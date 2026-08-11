"""SQLAlchemy model for auditable tool executions."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from enterprise_it_support.platform.database import Base


class ToolExecution(Base):
    """One final logical tool call, including rejected and failed attempts."""

    __tablename__ = "tool_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('succeeded', 'not_found', 'invalid_input', 'permission_denied', "
            "'timed_out', 'failed')",
            name="ck_tool_executions_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_tool_executions_nonnegative_attempts"),
        CheckConstraint("latency_ms >= 0", name="ck_tool_executions_nonnegative_latency"),
        Index("ix_tool_executions_run_started", "run_id", "started_at"),
        Index("ix_tool_executions_request_id", "request_id"),
        Index("ix_tool_executions_tool_name", "tool_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[str | None] = mapped_column(String(128))
    pending_confirmation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pending_confirmations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    request_id: Mapped[str] = mapped_column(String(128))
    node_name: Mapped[str] = mapped_column(String(100))
    tool_name: Mapped[str] = mapped_column(String(100))
    tool_version: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30))
    input_arguments: Mapped[dict[str, Any]] = mapped_column(JSONB)
    observation: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    required_risk_level: Mapped[str | None] = mapped_column(String(20))
    has_side_effect: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
