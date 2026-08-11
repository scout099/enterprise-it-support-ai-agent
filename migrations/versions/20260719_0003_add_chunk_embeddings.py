"""Add pgvector embeddings and indexing metadata to document chunks.

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260719_0003"
down_revision: str | Sequence[str] | None = "20260719_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a configurable-dimension vector and its generation profile."""
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_document_chunks_complete_embedding",
        "document_chunks",
        "(embedding IS NULL AND embedding_model IS NULL "
        "AND embedding_version IS NULL AND indexed_at IS NULL) OR "
        "(embedding IS NOT NULL AND embedding_model IS NOT NULL "
        "AND embedding_version IS NOT NULL AND indexed_at IS NOT NULL)",
    )
    op.create_index(
        "ix_document_chunks_embedding_profile",
        "document_chunks",
        ["embedding_model", "embedding_version"],
    )


def downgrade() -> None:
    """Remove chunk embeddings and their generation profile."""
    op.drop_index(
        "ix_document_chunks_embedding_profile",
        table_name="document_chunks",
    )
    op.drop_constraint(
        "ck_document_chunks_complete_embedding",
        "document_chunks",
        type_="check",
    )
    op.drop_column("document_chunks", "indexed_at")
    op.drop_column("document_chunks", "embedding_version")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding")
