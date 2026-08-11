"""Add durable approval resume completion marker.

Revision ID: 20260801_0011
Revises: 20260724_0010
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0011"
down_revision: str | Sequence[str] | None = "20260724_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record when the saved human decision has resumed its Agent Run."""
    op.add_column(
        "approval_requests",
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove the resume completion marker."""
    op.drop_column("approval_requests", "resumed_at")
