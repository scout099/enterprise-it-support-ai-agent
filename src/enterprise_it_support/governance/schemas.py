"""HTTP contracts for local human approval."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from enterprise_it_support.agent_runtime.schemas import AgentRunResponse
from enterprise_it_support.governance.domain import (
    ApprovalDecisionValue,
    ApprovalStatus,
    PolicyDecision,
    RiskLevel,
)


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)
    rationale: str | None = Field(default=None, max_length=1000)

    @field_validator("actor_id", "rationale")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class ApprovalDecisionResponse(BaseModel):
    id: UUID
    approval_request_id: UUID
    approver_user_id: UUID
    approver_external_id: str
    decision: ApprovalDecisionValue
    rationale: str | None
    decided_at: datetime


class ApprovalRequestResponse(BaseModel):
    id: UUID
    requester_user_id: UUID
    requester_external_id: str
    action: str
    tool: str
    target_resource: str
    risk_level: RiskLevel
    business_justification: str
    policy_decision: PolicyDecision
    status: ApprovalStatus
    idempotency_key: str
    source_agent_run_id: UUID
    checkpoint_node: str
    simulated_result: dict[str, object] | None
    created_at: datetime
    decided_at: datetime | None
    executed_at: datetime | None
    resumed_at: datetime | None
    decision: ApprovalDecisionResponse | None


class PendingApprovalListResponse(BaseModel):
    items: list[ApprovalRequestResponse]
    limit: int
    offset: int


class ApprovalOutcomeResponse(BaseModel):
    approval: ApprovalRequestResponse
    run: AgentRunResponse
