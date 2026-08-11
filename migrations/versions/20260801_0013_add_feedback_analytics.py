"""Add user feedback and cancellable confirmation state.

Revision ID: 20260801_0013
Revises: 20260801_0012
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0013"
down_revision: str | Sequence[str] | None = "20260801_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_pending_confirmations_status",
        "pending_confirmations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_pending_confirmations_status",
        "pending_confirmations",
        "status IN "
        "('pending', 'executing', 'executed', 'failed', 'cancelled', "
        "'approval_required')",
    )
    op.add_column(
        "pending_confirmations",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("satisfaction_rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "satisfaction_rating IS NULL OR "
            "(satisfaction_rating >= 1 AND satisfaction_rating <= 5)",
            name="ck_feedback_satisfaction_range",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_run_id", name="uq_feedback_agent_run"),
        sa.UniqueConstraint("idempotency_key", name="uq_feedback_idempotency_key"),
    )
    op.create_index("ix_feedback_actor_created", "feedback", ["actor_id", "created_at"])
    op.create_index("ix_feedback_created", "feedback", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_created", table_name="feedback")
    op.drop_index("ix_feedback_actor_created", table_name="feedback")
    op.drop_table("feedback")
    op.drop_column("pending_confirmations", "cancelled_at", if_exists=True)
    op.drop_constraint(
        "ck_pending_confirmations_status",
        "pending_confirmations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_pending_confirmations_status",
        "pending_confirmations",
        "status IN ('pending', 'executing', 'executed', 'failed', 'approval_required')",
    )
