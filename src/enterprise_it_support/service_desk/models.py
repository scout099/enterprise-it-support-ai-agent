"""SQLAlchemy models for the local Phase 8 service desk."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from enterprise_it_support.platform.database import Base


class Ticket(Base):
    """One local IT support ticket created through a confirmed action."""

    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_tickets_status",
        ),
        Index("ix_tickets_requester_created", "requester_id", "created_at"),
        Index("ix_tickets_status_updated", "status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_number: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="open")
    requester_id: Mapped[str] = mapped_column(String(128), index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(128))
    source_conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    diagnosis_summary: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TicketComment(Base):
    """One idempotent comment appended to a local ticket."""

    __tablename__ = "ticket_comments"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ticket_comments_idempotency_key"),
        Index("ix_ticket_comments_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
    )
    author_id: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PendingConfirmation(Base):
    """A validated R1 confirmation or non-executable R3 approval request."""

    __tablename__ = "pending_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "action",
            "idempotency_key",
            name="uq_pending_confirmations_action_idempotency",
        ),
        CheckConstraint(
            "risk_level IN ('r1', 'r3')",
            name="ck_pending_confirmations_risk",
        ),
        CheckConstraint(
            "status IN "
            "('pending', 'executing', 'executed', 'failed', 'cancelled', "
            "'approval_required')",
            name="ck_pending_confirmations_status",
        ),
        Index("ix_pending_confirmations_actor_created", "actor_id", "created_at"),
        Index("ix_pending_confirmations_run", "source_agent_run_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[str] = mapped_column(String(128))
    actor_role: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    risk_level: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB)
    parameters_summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    impact_summary: Mapped[str] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    source_agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """Sanitized append-only policy and execution audit event."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "policy_decision IN "
            "('allow', 'deny', 'confirmation_required', 'approval_required', "
            "'require_confirmation', 'require_approval', 'need_more_context')",
            name="ck_audit_events_policy_decision",
        ),
        Index("ix_audit_events_created", "created_at", "id"),
        Index("ix_audit_events_actor", "actor", "created_at"),
        Index("ix_audit_events_request", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(300))
    parameters_summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    policy_decision: Mapped[str] = mapped_column(String(40))
    execution_result: Mapped[str] = mapped_column(String(100))
    request_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
