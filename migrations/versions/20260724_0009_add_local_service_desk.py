"""Add local tickets, confirmations, write-tool metadata, and audit events.

Revision ID: 20260724_0009
Revises: 20260723_0008
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260724_0009"
down_revision: str | Sequence[str] | None = "20260723_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the Phase 8 local service-desk schema."""
    op.execute(sa.text("CREATE SEQUENCE ticket_number_seq START WITH 1"))
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_number", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requester_id", sa.String(length=128), nullable=False),
        sa.Column("assigned_to", sa.String(length=128), nullable=True),
        sa.Column("source_conversation_id", sa.Uuid(), nullable=True),
        sa.Column("source_agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("diagnosis_summary", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_tickets_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_agent_run_id"],
            ["agent_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_tickets_requester_id", "tickets", ["requester_id"], unique=False)
    op.create_index(
        "ix_tickets_requester_created",
        "tickets",
        ["requester_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_tickets_status_updated",
        "tickets",
        ["status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_ticket_comments_idempotency_key",
        ),
    )
    op.create_index(
        "ix_ticket_comments_ticket_id",
        "ticket_comments",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_comments_ticket_created",
        "ticket_comments",
        ["ticket_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "pending_confirmations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "parameters_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("impact_summary", sa.String(length=500), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("source_conversation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "risk_level IN ('r1', 'r3')",
            name="ck_pending_confirmations_risk",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'executing', 'executed', 'failed', 'approval_required')",
            name="ck_pending_confirmations_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_agent_run_id"],
            ["agent_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action",
            "idempotency_key",
            name="uq_pending_confirmations_action_idempotency",
        ),
    )
    op.create_index(
        "ix_pending_confirmations_actor_created",
        "pending_confirmations",
        ["actor_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_pending_confirmations_run",
        "pending_confirmations",
        ["source_agent_run_id"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target", sa.String(length=300), nullable=False),
        sa.Column(
            "parameters_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("policy_decision", sa.String(length=40), nullable=False),
        sa.Column("execution_result", sa.String(length=100), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "policy_decision IN ('allow', 'deny', 'confirmation_required', 'approval_required')",
            name="ck_audit_events_policy_decision",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_created",
        "audit_events",
        ["created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_actor",
        "audit_events",
        ["actor", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_request",
        "audit_events",
        ["request_id"],
        unique=False,
    )

    op.drop_constraint(
        "ck_tool_executions_read_only",
        "tool_executions",
        type_="check",
    )
    op.alter_column("tool_executions", "run_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column(
        "tool_executions",
        sa.Column("actor_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("pending_confirmation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_foreign_key(
        "fk_tool_executions_pending_confirmation",
        "tool_executions",
        "pending_confirmations",
        ["pending_confirmation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tool_executions_pending_confirmation_id",
        "tool_executions",
        ["pending_confirmation_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_executions_idempotency_key",
        "tool_executions",
        ["idempotency_key"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Phase 8 schema and restore the Phase 7 read-only invariant."""
    op.execute(
        sa.text(
            "DELETE FROM tool_executions "
            "WHERE run_id IS NULL OR has_side_effect = true "
            "OR tool_name IN "
            "('create_ticket', 'add_ticket_comment', 'get_ticket_status')"
        )
    )
    op.drop_index("ix_tool_executions_idempotency_key", table_name="tool_executions")
    op.drop_index(
        "ix_tool_executions_pending_confirmation_id",
        table_name="tool_executions",
    )
    op.drop_constraint(
        "fk_tool_executions_pending_confirmation",
        "tool_executions",
        type_="foreignkey",
    )
    op.drop_column("tool_executions", "idempotency_key")
    op.drop_column("tool_executions", "pending_confirmation_id")
    op.drop_column("tool_executions", "actor_id")
    op.alter_column("tool_executions", "run_id", existing_type=sa.Uuid(), nullable=False)
    op.create_check_constraint(
        "ck_tool_executions_read_only",
        "tool_executions",
        "has_side_effect = false",
    )

    op.drop_index("ix_audit_events_request", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(
        "ix_pending_confirmations_run",
        table_name="pending_confirmations",
    )
    op.drop_index(
        "ix_pending_confirmations_actor_created",
        table_name="pending_confirmations",
    )
    op.drop_table("pending_confirmations")
    op.drop_index(
        "ix_ticket_comments_ticket_created",
        table_name="ticket_comments",
    )
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")
    op.drop_index("ix_tickets_status_updated", table_name="tickets")
    op.drop_index("ix_tickets_requester_created", table_name="tickets")
    op.drop_index("ix_tickets_requester_id", table_name="tickets")
    op.drop_table("tickets")
    op.execute(sa.text("DROP SEQUENCE ticket_number_seq"))
