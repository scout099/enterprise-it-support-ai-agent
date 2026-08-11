"""Add append-only audit rows for controlled tool executions.

Revision ID: 20260723_0008
Revises: 20260723_0007
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0008"
down_revision: str | Sequence[str] | None = "20260723_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the read-only tool execution audit table."""
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("tool_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "input_arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "observation",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("required_risk_level", sa.String(length=20), nullable=True),
        sa.Column(
            "has_side_effect",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
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
            "status IN "
            "('succeeded', 'not_found', 'invalid_input', 'permission_denied', "
            "'timed_out', 'failed')",
            name="ck_tool_executions_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_tool_executions_nonnegative_attempts",
        ),
        sa.CheckConstraint(
            "latency_ms >= 0",
            name="ck_tool_executions_nonnegative_latency",
        ),
        sa.CheckConstraint(
            "has_side_effect = false",
            name="ck_tool_executions_read_only",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_executions_run_id",
        "tool_executions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_executions_run_started",
        "tool_executions",
        ["run_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_tool_executions_request_id",
        "tool_executions",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_executions_tool_name",
        "tool_executions",
        ["tool_name"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the Phase 7 tool audit table."""
    op.drop_index("ix_tool_executions_tool_name", table_name="tool_executions")
    op.drop_index("ix_tool_executions_request_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_run_started", table_name="tool_executions")
    op.drop_index("ix_tool_executions_run_id", table_name="tool_executions")
    op.drop_table("tool_executions")
