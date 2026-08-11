"""Domain records and errors for feedback and dashboard analytics."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


class FeedbackNotFoundError(LookupError):
    """The referenced Agent Run or Ticket does not exist."""


class FeedbackAccessDeniedError(PermissionError):
    """The caller does not own the referenced Agent Run or Ticket."""


class FeedbackConflictError(ValueError):
    """Feedback idempotency or one-per-run semantics conflict."""


@dataclass(frozen=True)
class FeedbackCreate:
    agent_run_id: UUID
    actor_id: str
    user_role: str
    resolved: bool
    satisfaction_rating: int | None
    comment: str | None
    ticket_number: str | None
    idempotency_key: str


@dataclass(frozen=True)
class StoredFeedback:
    id: UUID
    agent_run_id: UUID
    conversation_id: UUID | None
    ticket_number: str | None
    actor_id: str
    resolved: bool
    satisfaction_rating: int | None
    comment: str | None
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True)
class RawAnalytics:
    summary: dict[str, Any]
    ticket_categories: tuple[dict[str, Any], ...]
    issue_counts: tuple[dict[str, Any], ...]
    satisfaction_distribution: tuple[dict[str, Any], ...]
    failure_reasons: tuple[dict[str, Any], ...]
