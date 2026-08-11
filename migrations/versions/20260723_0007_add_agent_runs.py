"""Add recoverable Agent Run and append-only Agent Step audit tables.

Revision ID: 20260723_0007
Revises: 20260722_0006
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0007"
down_revision: str | Sequence[str] | None = "20260722_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Agent business trace tables; LangGraph owns its checkpoint tables separately."""
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("intent_confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("current_node", sa.String(length=100), nullable=True),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'needs_clarification', 'escalated', 'failed')",
            name="ck_agent_runs_status",
        ),
        sa.CheckConstraint(
            "intent_confidence >= 0 AND intent_confidence <= 1",
            name="ck_agent_runs_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_request_id", "agent_runs", ["request_id"], unique=False)
    op.create_index(
        "ix_agent_runs_conversation_id",
        "agent_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index("ix_agent_runs_started_at", "agent_runs", ["started_at"], unique=False)

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_agent_steps_positive_sequence",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_agent_steps_status",
        ),
        sa.CheckConstraint(
            "latency_ms >= 0",
            name="ck_agent_steps_nonnegative_latency",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "sequence_number",
            name="uq_agent_steps_run_sequence",
        ),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"], unique=False)
    op.create_index(
        "ix_agent_steps_run_started",
        "agent_steps",
        ["run_id", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Agent trace tables without touching LangGraph-managed checkpoint tables."""
    op.drop_index("ix_agent_steps_run_started", table_name="agent_steps")
    op.drop_index("ix_agent_steps_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index("ix_agent_runs_started_at", table_name="agent_runs")
    op.drop_index("ix_agent_runs_conversation_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_request_id", table_name="agent_runs")
    op.drop_table("agent_runs")
