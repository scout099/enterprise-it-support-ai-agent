"""Persist success, refusal, and safe failure outcomes for every chat turn.

Revision ID: 20260722_0006
Revises: 20260722_0005
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0006"
down_revision: str | Sequence[str] | None = "20260722_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit turn outcome and safe error classification columns."""
    op.add_column("messages", sa.Column("status", sa.String(length=20), nullable=True))
    op.add_column("messages", sa.Column("error_stage", sa.String(length=20), nullable=True))
    op.add_column("messages", sa.Column("error_code", sa.String(length=100), nullable=True))
    op.execute(
        "UPDATE messages SET status = CASE "
        "WHEN model_provider = 'not_called' THEN 'refused' ELSE 'succeeded' END "
        "WHERE role = 'assistant'"
    )
    op.create_check_constraint(
        "ck_messages_status",
        "messages",
        "status IS NULL OR status IN ('succeeded', 'refused', 'failed')",
    )
    op.create_check_constraint(
        "ck_messages_error_stage",
        "messages",
        "error_stage IS NULL OR error_stage IN ('retrieval', 'model', 'validation', 'citation')",
    )
    op.create_check_constraint(
        "ck_messages_trace_outcome",
        "messages",
        "(role = 'user' AND status IS NULL AND error_stage IS NULL "
        "AND error_code IS NULL AND response IS NULL) OR "
        "(role = 'assistant' AND status IN ('succeeded', 'refused') "
        "AND error_stage IS NULL AND error_code IS NULL AND response IS NOT NULL) OR "
        "(role = 'assistant' AND status = 'failed' AND error_stage IS NOT NULL "
        "AND error_code IS NOT NULL AND response IS NULL)",
    )


def downgrade() -> None:
    """Remove explicit turn outcome columns."""
    op.drop_constraint("ck_messages_trace_outcome", "messages", type_="check")
    op.drop_constraint("ck_messages_error_stage", "messages", type_="check")
    op.drop_constraint("ck_messages_status", "messages", type_="check")
    op.drop_column("messages", "error_code")
    op.drop_column("messages", "error_stage")
    op.drop_column("messages", "status")
