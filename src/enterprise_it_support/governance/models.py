"""SQLAlchemy models for local RBAC and simulated human approval."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enterprise_it_support.platform.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint(
            "requester_user_id",
            "idempotency_key",
            name="uq_approval_requests_requester_idempotency",
        ),
        UniqueConstraint(
            "source_agent_run_id",
            name="uq_approval_requests_source_agent_run",
        ),
        CheckConstraint("risk_level IN ('r0', 'r1', 'r2', 'r3', 'r4')", name="ck_approval_risk"),
        CheckConstraint(
            "policy_decision IN "
            "('allow', 'deny', 'require_confirmation', 'require_approval', "
            "'need_more_context')",
            name="ck_approval_policy_decision",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'executed')",
            name="ck_approval_status",
        ),
        Index("ix_approval_requests_status_created", "status", "created_at", "id"),
        Index("ix_approval_requests_requester", "requester_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    requester_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    action: Mapped[str] = mapped_column(String(100))
    tool: Mapped[str] = mapped_column(String(150))
    target_resource: Mapped[str] = mapped_column(String(300))
    risk_level: Mapped[str] = mapped_column(String(10))
    business_justification: Mapped[str] = mapped_column(Text)
    request_context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    policy_decision: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    source_agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
    )
    checkpoint_node: Mapped[str] = mapped_column(String(100))
    simulated_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decision: Mapped["ApprovalDecision | None"] = relationship(
        back_populates="request",
        uselist=False,
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('approve', 'reject')", name="ck_approval_decision_value"),
        Index("ix_approval_decisions_approver", "approver_user_id", "decided_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    approval_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        unique=True,
    )
    approver_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    decision: Mapped[str] = mapped_column(String(20))
    rationale: Mapped[str | None] = mapped_column(String(1000))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[ApprovalRequest] = relationship(back_populates="decision")
