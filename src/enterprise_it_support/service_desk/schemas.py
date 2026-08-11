"""HTTP schemas for Agent action proposals, confirmations, tickets, and audit."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from enterprise_it_support.agent_runtime.schemas import AgentRunResponse
from enterprise_it_support.service_desk.domain import (
    ActionRisk,
    ConfirmationStatus,
    PolicyDecision,
)


class AgentRespondRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=2000)
    actor_id: str = Field(min_length=1, max_length=128)
    user_role: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=128)
    business_justification: str | None = Field(
        default=None,
        min_length=10,
        max_length=2000,
    )
    conversation_id: UUID | None = None
    ticket_number: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator(
        "user_message",
        "actor_id",
        "user_role",
        "idempotency_key",
        "business_justification",
    )
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class PendingConfirmationResponse(BaseModel):
    id: UUID
    action: str
    risk_level: ActionRisk
    status: ConfirmationStatus
    parameters: dict[str, Any]
    parameters_summary: dict[str, Any]
    impact_summary: str
    idempotency_key: str
    source_agent_run_id: UUID | None
    source_conversation_id: UUID | None
    result: dict[str, Any] | None
    error_code: str | None
    created_at: datetime
    confirmed_at: datetime | None
    executed_at: datetime | None
    cancelled_at: datetime | None


class AgentRespondResponse(BaseModel):
    run: AgentRunResponse
    pending_confirmation: PendingConfirmationResponse | None


class AgentConfirmRequest(BaseModel):
    confirmation_id: UUID
    actor_id: str = Field(min_length=1, max_length=128)
    user_role: str = Field(min_length=1, max_length=100)

    @field_validator("actor_id", "user_role")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class AgentCancelRequest(BaseModel):
    confirmation_id: UUID
    actor_id: str = Field(min_length=1, max_length=128)
    user_role: str = Field(min_length=1, max_length=100)

    @field_validator("actor_id", "user_role")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class TicketResponse(BaseModel):
    ticket_id: UUID
    ticket_number: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    requester_id: str
    assigned_to: str | None
    source_conversation_id: UUID | None
    source_agent_run_id: UUID | None
    diagnosis_summary: str
    created_at: str
    updated_at: str
    comments: list[dict[str, Any]]


class AuditEventResponse(BaseModel):
    id: UUID
    actor: str
    action: str
    target: str
    parameters_summary: dict[str, Any]
    policy_decision: PolicyDecision
    execution_result: str
    request_id: str
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    limit: int
    offset: int
