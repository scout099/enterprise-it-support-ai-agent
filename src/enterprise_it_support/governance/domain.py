"""Domain contracts for deterministic RBAC, risk policy, and local approvals."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

FINANCE_ADMIN_ACTION = "join_finance_admin_group"
FINANCE_ADMIN_TOOL = "simulate_finance_admin_group_membership"
FINANCE_ADMIN_TARGET = "group:finance-system-administrators"
FINANCE_ADMIN_REQUEST_PERMISSION = "finance_admin_group:request"
APPROVAL_READ_PERMISSION = "approval:read"
APPROVAL_DECIDE_PERMISSION = "approval:decide"


class RiskLevel(StrEnum):
    """Application-owned enterprise action risk classification."""

    R0 = "r0"
    R1 = "r1"
    R2 = "r2"
    R3 = "r3"
    R4 = "r4"


class PolicyDecision(StrEnum):
    """The only decisions the deterministic Policy Engine may return."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_APPROVAL = "require_approval"
    NEED_MORE_CONTEXT = "need_more_context"


class ApprovalStatus(StrEnum):
    """Lifecycle of one high-risk approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ApprovalDecisionValue(StrEnum):
    """Immutable human decision on one approval request."""

    APPROVE = "approve"
    REJECT = "reject"


class GovernanceError(RuntimeError):
    """Base error for stable governance failures."""

    code = "governance_error"


class LocalUserNotFoundError(GovernanceError):
    code = "governance_user_not_found"


class GovernanceAccessDeniedError(GovernanceError):
    code = "governance_access_denied"


class ApprovalRequestNotFoundError(GovernanceError):
    code = "approval_request_not_found"


class ApprovalAlreadyDecidedError(GovernanceError):
    code = "approval_already_decided"


class ApprovalConflictError(GovernanceError):
    code = "approval_conflict"


@dataclass(frozen=True)
class StoredUser:
    id: UUID
    external_id: str
    display_name: str
    is_active: bool
    roles: frozenset[str]
    permissions: frozenset[str]


@dataclass(frozen=True)
class PolicyInput:
    user: StoredUser
    role: str
    action: str
    tool: str
    target_resource: str
    risk_level: RiskLevel
    request_context: dict[str, Any]


@dataclass(frozen=True)
class StoredApprovalDecision:
    id: UUID
    approval_request_id: UUID
    approver_user_id: UUID
    approver_external_id: str
    decision: ApprovalDecisionValue
    rationale: str | None
    decided_at: datetime


@dataclass(frozen=True)
class StoredApprovalRequest:
    id: UUID
    requester_user_id: UUID
    requester_external_id: str
    action: str
    tool: str
    target_resource: str
    risk_level: RiskLevel
    business_justification: str
    request_context: dict[str, Any]
    policy_decision: PolicyDecision
    status: ApprovalStatus
    idempotency_key: str
    source_agent_run_id: UUID
    checkpoint_node: str
    simulated_result: dict[str, Any] | None
    created_at: datetime
    decided_at: datetime | None
    executed_at: datetime | None
    resumed_at: datetime | None
    decision: StoredApprovalDecision | None
