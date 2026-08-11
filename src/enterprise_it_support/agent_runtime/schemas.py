"""HTTP contracts for Agent Runtime execution and trace reads."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from enterprise_it_support.agent_runtime.state import (
    AgentIntent,
    AgentRunStatus,
    AgentStepStatus,
    RiskLevel,
)
from enterprise_it_support.tools.contracts import ToolExecutionStatus, ToolRiskLevel


class AgentRunRequest(BaseModel):
    """Bounded input for one new Agent graph run."""

    user_message: str = Field(min_length=1, max_length=2000)
    user_role: str = Field(min_length=1, max_length=100)
    conversation_id: UUID | None = None

    @field_validator("user_message", "user_role")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class AgentStepResponse(BaseModel):
    """One persisted node attempt in execution order."""

    id: UUID
    sequence_number: int
    node_name: str
    status: AgentStepStatus
    error_code: str | None
    latency_ms: int
    started_at: datetime
    completed_at: datetime


class ToolExecutionResponse(BaseModel):
    """One persisted, sanitized logical tool-call audit record."""

    id: UUID
    node_name: str
    tool_name: str
    tool_version: str | None
    status: ToolExecutionStatus
    observation: dict[str, Any] | None
    risk_level: ToolRiskLevel | None
    has_side_effect: bool
    error_code: str | None
    error_message: str | None
    attempts: int
    latency_ms: int
    started_at: datetime
    completed_at: datetime


class AgentRunResponse(BaseModel):
    """Latest recoverable Agent state plus its complete node trace."""

    run_id: UUID
    request_id: str
    conversation_id: UUID | None
    status: AgentRunStatus
    intent: AgentIntent | None
    intent_confidence: float
    risk_level: RiskLevel
    missing_information: list[str]
    reasoning_summary: str
    retrieved_evidence: list[dict[str, Any]]
    planned_steps: list[str]
    tool_results: list[dict[str, Any]]
    tool_call_count: int
    diagnostic_context: dict[str, Any]
    escalation_reason: str | None
    tool_executions: list[ToolExecutionResponse]
    classification_metadata: dict[str, Any] | None
    final_response: dict[str, Any] | None
    error: dict[str, str] | None
    retry_count: int
    node_count: int
    current_node: str | None
    governance_action: str | None
    governance_risk_level: str | None
    governance_policy_decision: str | None
    approval_request_id: UUID | None
    approval_decision: str | None
    simulated_execution: dict[str, Any] | None
    started_at: datetime
    completed_at: datetime | None
    steps: list[AgentStepResponse]
