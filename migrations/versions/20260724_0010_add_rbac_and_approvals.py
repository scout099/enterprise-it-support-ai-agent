"""Add deterministic RBAC and human approval workflow.

Revision ID: 20260724_0010
Revises: 20260724_0009
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260724_0010"
down_revision: str | Sequence[str] | None = "20260724_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLE_IDS = {
    "employee": "10000000-0000-0000-0000-000000000001",
    "helpdesk": "10000000-0000-0000-0000-000000000002",
    "engineer": "10000000-0000-0000-0000-000000000003",
    "admin": "10000000-0000-0000-0000-000000000004",
    "approver": "10000000-0000-0000-0000-000000000005",
}
PERMISSION_IDS = {
    "finance_admin_group:request": "20000000-0000-0000-0000-000000000001",
    "approval:read": "20000000-0000-0000-0000-000000000002",
    "approval:decide": "20000000-0000-0000-0000-000000000003",
}
USER_IDS = {
    "employee-demo": "30000000-0000-0000-0000-000000000001",
    "helpdesk-demo": "30000000-0000-0000-0000-000000000002",
    "engineer-demo": "30000000-0000-0000-0000-000000000003",
    "admin-demo": "30000000-0000-0000-0000-000000000004",
    "approver-demo": "30000000-0000-0000-0000-000000000005",
}


def upgrade() -> None:
    """Create Phase 9 RBAC and approval persistence."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    role_rows = [
        {"id": ROLE_IDS[name], "name": name, "description": f"Local demo {name} role"}
        for name in ROLE_IDS
    ]
    permission_rows = [
        {"id": value, "name": name, "description": f"Local permission {name}"}
        for name, value in PERMISSION_IDS.items()
    ]
    user_rows = [
        {
            "id": USER_IDS[external_id],
            "external_id": external_id,
            "display_name": external_id.replace("-", " ").title(),
        }
        for external_id in USER_IDS
    ]
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("description", sa.String()),
        ),
        role_rows,
    )
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("description", sa.String()),
        ),
        permission_rows,
    )
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.Uuid()),
            sa.column("external_id", sa.String()),
            sa.column("display_name", sa.String()),
            sa.column("is_active", sa.Boolean()),
        ),
        [{**row, "is_active": True} for row in user_rows],
    )
    op.bulk_insert(
        sa.table(
            "user_roles",
            sa.column("user_id", sa.Uuid()),
            sa.column("role_id", sa.Uuid()),
        ),
        [
            {
                "user_id": USER_IDS[f"{role}-demo"],
                "role_id": ROLE_IDS[role],
            }
            for role in ROLE_IDS
        ],
    )
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.Uuid()),
            sa.column("permission_id", sa.Uuid()),
        ),
        [
            {
                "role_id": role_id,
                "permission_id": PERMISSION_IDS["finance_admin_group:request"],
            }
            for role_id in ROLE_IDS.values()
        ]
        + [
            {
                "role_id": ROLE_IDS[role],
                "permission_id": PERMISSION_IDS[permission],
            }
            for role in ("admin", "approver")
            for permission in ("approval:read", "approval:decide")
        ],
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("tool", sa.String(length=150), nullable=False),
        sa.Column("target_resource", sa.String(length=300), nullable=False),
        sa.Column("risk_level", sa.String(length=10), nullable=False),
        sa.Column("business_justification", sa.Text(), nullable=False),
        sa.Column(
            "request_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("policy_decision", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source_agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_node", sa.String(length=100), nullable=False),
        sa.Column(
            "simulated_result",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "risk_level IN ('r0', 'r1', 'r2', 'r3', 'r4')",
            name="ck_approval_risk",
        ),
        sa.CheckConstraint(
            "policy_decision IN "
            "('allow', 'deny', 'require_confirmation', 'require_approval', "
            "'need_more_context')",
            name="ck_approval_policy_decision",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'executed')",
            name="ck_approval_status",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_user_id",
            "idempotency_key",
            name="uq_approval_requests_requester_idempotency",
        ),
        sa.UniqueConstraint(
            "source_agent_run_id",
            name="uq_approval_requests_source_agent_run",
        ),
    )
    op.create_index(
        "ix_approval_requests_status_created",
        "approval_requests",
        ["status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_approval_requests_requester",
        "approval_requests",
        ["requester_user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_request_id", sa.Uuid(), nullable=False),
        sa.Column("approver_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("rationale", sa.String(length=1000), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_approval_decision_value",
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["approval_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approver_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_request_id"),
    )
    op.create_index(
        "ix_approval_decisions_approver",
        "approval_decisions",
        ["approver_user_id", "decided_at"],
        unique=False,
    )

    op.drop_constraint("ck_agent_runs_status", "agent_runs", type_="check")
    op.create_check_constraint(
        "ck_agent_runs_status",
        "agent_runs",
        "status IN "
        "('running', 'waiting_approval', 'completed', 'needs_clarification', "
        "'escalated', 'failed')",
    )
    op.drop_constraint("ck_audit_events_policy_decision", "audit_events", type_="check")
    op.create_check_constraint(
        "ck_audit_events_policy_decision",
        "audit_events",
        "policy_decision IN "
        "('allow', 'deny', 'confirmation_required', 'approval_required', "
        "'require_confirmation', 'require_approval', 'need_more_context')",
    )


def downgrade() -> None:
    """Remove Phase 9 governance while preserving the Phase 8 schema."""
    op.execute(
        sa.text(
            "UPDATE agent_runs SET status = 'failed', "
            "error_code = 'approval_workflow_removed' "
            "WHERE status = 'waiting_approval'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE audit_events SET policy_decision = "
            "CASE policy_decision "
            "WHEN 'require_confirmation' THEN 'confirmation_required' "
            "WHEN 'require_approval' THEN 'approval_required' "
            "WHEN 'need_more_context' THEN 'deny' "
            "ELSE policy_decision END"
        )
    )
    op.drop_constraint("ck_audit_events_policy_decision", "audit_events", type_="check")
    op.create_check_constraint(
        "ck_audit_events_policy_decision",
        "audit_events",
        "policy_decision IN ('allow', 'deny', 'confirmation_required', 'approval_required')",
    )
    op.drop_constraint("ck_agent_runs_status", "agent_runs", type_="check")
    op.create_check_constraint(
        "ck_agent_runs_status",
        "agent_runs",
        "status IN ('running', 'completed', 'needs_clarification', 'escalated', 'failed')",
    )
    op.drop_index("ix_approval_decisions_approver", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index("ix_approval_requests_requester", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status_created", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
