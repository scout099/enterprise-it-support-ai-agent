"""HTTP schemas for feedback capture and backend analytics."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FeedbackCreateRequest(BaseModel):
    agent_run_id: UUID
    actor_id: str = Field(min_length=1, max_length=128)
    user_role: str = Field(min_length=1, max_length=100)
    resolved: bool
    satisfaction_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    ticket_number: str | None = Field(default=None, min_length=1, max_length=40)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("actor_id", "user_role", "comment", "ticket_number", "idempotency_key")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class FeedbackResponse(BaseModel):
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


class MetricResponse(BaseModel):
    value: float | None
    sample_count: int = Field(ge=0)


class CountItemResponse(BaseModel):
    label: str
    count: int = Field(ge=0)


class EvaluationSummaryResponse(BaseModel):
    run_id: str
    created_at: datetime
    gate_passed: bool
    dataset_version: str
    intent_accuracy: float | None
    workflow_completion_rate: float | None
    citation_validity: float | None
    failed_case_count: int = Field(ge=0)


class AnalyticsSummaryResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    total_agent_runs: int = Field(ge=0)
    total_tickets: int = Field(ge=0)
    ticket_categories: list[CountItemResponse]
    issue_counts: list[CountItemResponse]
    self_service_resolution_rate: MetricResponse
    human_transfer_rate: MetricResponse
    average_agent_steps: MetricResponse
    average_tool_calls: MetricResponse
    average_response_time_ms: MetricResponse
    tool_success_rate: MetricResponse
    average_satisfaction: MetricResponse
    satisfaction_distribution: list[CountItemResponse]
    frequent_failure_reasons: list[CountItemResponse]
    recent_evaluations: list[EvaluationSummaryResponse]
