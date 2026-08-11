"""SQLAlchemy model for user resolution and satisfaction feedback."""

from datetime import datetime
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
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from enterprise_it_support.platform.database import Base


class Feedback(Base):
    """One idempotent user outcome for a completed Agent Run."""

    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("agent_run_id", name="uq_feedback_agent_run"),
        UniqueConstraint("idempotency_key", name="uq_feedback_idempotency_key"),
        CheckConstraint(
            "satisfaction_rating IS NULL OR "
            "(satisfaction_rating >= 1 AND satisfaction_rating <= 5)",
            name="ck_feedback_satisfaction_range",
        ),
        Index("ix_feedback_created", "created_at", "id"),
        Index("ix_feedback_actor_created", "actor_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    ticket_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_id: Mapped[str] = mapped_column(String(128))
    resolved: Mapped[bool] = mapped_column(Boolean)
    satisfaction_rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
