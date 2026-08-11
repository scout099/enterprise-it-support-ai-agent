"""Add document retrieval permissions and a PostgreSQL full-text index.

Revision ID: 20260722_0004
Revises: 20260719_0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260722_0004"
down_revision: str | Sequence[str] | None = "20260719_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pre-retrieval authorization metadata and keyword-search support."""
    op.add_column(
        "documents",
        sa.Column(
            "visibility",
            sa.String(length=20),
            server_default="public",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "allowed_roles",
            postgresql.ARRAY(sa.String(length=100)),
            server_default="{}",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_documents_visibility",
        "documents",
        "visibility IN ('public', 'role_restricted')",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_fts ON document_chunks USING gin "
        "(to_tsvector('simple', coalesce(section_title, '') || ' ' || content))"
    )


def downgrade() -> None:
    """Remove retrieval-specific metadata and indexes."""
    op.drop_index("ix_document_chunks_fts", table_name="document_chunks")
    op.drop_constraint("ck_documents_visibility", "documents", type_="check")
    op.drop_column("documents", "allowed_roles")
    op.drop_column("documents", "visibility")
