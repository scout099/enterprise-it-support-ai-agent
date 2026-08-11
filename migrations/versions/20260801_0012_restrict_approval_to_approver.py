"""Restrict seeded approval authority to the approver role.

Revision ID: 20260801_0012
Revises: 20260801_0011
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0012"
down_revision: str | Sequence[str] | None = "20260801_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove approval read/decide from the admin-only demo role."""
    op.execute(
        sa.text(
            "DELETE FROM role_permissions rp "
            "USING roles r, permissions p "
            "WHERE rp.role_id = r.id "
            "AND rp.permission_id = p.id "
            "AND r.name = 'admin' "
            "AND p.name IN ('approval:read', 'approval:decide')"
        )
    )


def downgrade() -> None:
    """Restore the original Phase 9 admin approval seed mapping."""
    op.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r CROSS JOIN permissions p "
            "WHERE r.name = 'admin' "
            "AND p.name IN ('approval:read', 'approval:decide') "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )
    )
