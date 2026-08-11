"""Public domain contracts for local tickets and confirmed actions."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    APPROVAL_REQUIRED = "approval_required"


class ActionRisk(StrEnum):
    R0 = "r0"
    R1 = "r1"
    R3 = "r3"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRMATION_REQUIRED = "confirmation_required"
    APPROVAL_REQUIRED = "approval_required"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_APPROVAL = "require_approval"
    NEED_MORE_CONTEXT = "need_more_context"


class IdempotencyConflictError(ValueError):
    """The same key was reused for a materially different action."""


class ConfirmationNotFoundError(LookupError):
    """The requested pending confirmation does not exist."""


class ConfirmationAccessDeniedError(PermissionError):
    """The caller does not own the confirmation and lacks support authority."""


class ConfirmationStateError(RuntimeError):
    """The confirmation lifecycle does not permit execution."""


class TicketNotFoundError(LookupError):
    """The requested ticket does not exist."""


@dataclass(frozen=True)
class AtomicToolAuditContext:
    execution_id: UUID
    run_id: UUID | None
    actor_id: str
    pending_confirmation_id: UUID
    idempotency_key: str
    request_id: str
    node_name: str


@dataclass(frozen=True)
class TicketCreateCommand:
    title: str
    description: str
    category: str
    priority: TicketPriority
    requester_id: str
    assigned_to: str | None
    source_conversation_id: UUID | None
    source_agent_run_id: UUID | None
    diagnosis_summary: str
    idempotency_key: str
    request_id: str
    tool_audit: AtomicToolAuditContext


@dataclass(frozen=True)
class StoredTicket:
    id: UUID
    ticket_number: str
    title: str
    description: str
    category: str
    priority: TicketPriority
    status: TicketStatus
    requester_id: str
    assigned_to: str | None
    source_conversation_id: UUID | None
    source_agent_run_id: UUID | None
    diagnosis_summary: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime

    def as_tool_result(self) -> dict[str, Any]:
        return {
            "ticket_id": str(self.id),
            "ticket_number": self.ticket_number,
            "title": self.title,
            "category": self.category,
            "priority": self.priority.value,
            "status": self.status.value,
            "requester_id": self.requester_id,
            "assigned_to": self.assigned_to,
            "source_conversation_id": (
                None if self.source_conversation_id is None else str(self.source_conversation_id)
            ),
            "source_agent_run_id": (
                None if self.source_agent_run_id is None else str(self.source_agent_run_id)
            ),
            "diagnosis_summary": self.diagnosis_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class StoredTicketComment:
    id: UUID
    ticket_id: UUID
    author_id: str
    body: str
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True)
class PendingConfirmationCreate:
    actor_id: str
    actor_role: str
    action: str
    risk_level: ActionRisk
    status: ConfirmationStatus
    parameters: dict[str, Any]
    parameters_summary: dict[str, Any]
    impact_summary: str
    idempotency_key: str
    request_fingerprint: str
    source_agent_run_id: UUID | None
    source_conversation_id: UUID | None


@dataclass(frozen=True)
class StoredPendingConfirmation:
    id: UUID
    actor_id: str
    actor_role: str
    action: str
    risk_level: ActionRisk
    status: ConfirmationStatus
    parameters: dict[str, Any]
    parameters_summary: dict[str, Any]
    impact_summary: str
    idempotency_key: str
    request_fingerprint: str
    source_agent_run_id: UUID | None
    source_conversation_id: UUID | None
    result: dict[str, Any] | None
    error_code: str | None
    created_at: datetime
    confirmed_at: datetime | None
    executed_at: datetime | None
    cancelled_at: datetime | None


@dataclass(frozen=True)
class AuditEventCreate:
    actor: str
    action: str
    target: str
    parameters_summary: dict[str, Any]
    policy_decision: PolicyDecision
    execution_result: str
    request_id: str


@dataclass(frozen=True)
class StoredAuditEvent:
    id: UUID
    actor: str
    action: str
    target: str
    parameters_summary: dict[str, Any]
    policy_decision: PolicyDecision
    execution_result: str
    request_id: str
    created_at: datetime
