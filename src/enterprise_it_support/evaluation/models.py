"""Provider-neutral observations and deterministic Phase 10 evaluation results."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from enterprise_it_support.evaluation.dataset import EvaluationCategory


class ToolCallObservation(BaseModel):
    """One actual registered tool execution, including its audited input."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: dict[str, Any]
    status: str
    error_code: str | None = None
    latency_ms: int = Field(ge=0)


class TokenUsageObservation(BaseModel):
    """Provider-reported usage accumulated only for the Agent under evaluation."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)


class AgentObservation(BaseModel):
    """Raw case output captured from public runtime and persistence seams."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvaluationCategory
    actual_intent: str | None
    retrieved_document_titles: list[str]
    retrieved_chunk_ids: list[str]
    evidence_texts: list[str]
    citation_document_titles: list[str]
    citation_chunk_ids: list[str]
    tool_calls: list[ToolCallObservation]
    final_status: str
    final_response: dict[str, Any] | None
    refused: bool | None
    claims: list[str]
    actual_actions: list[str]
    steps: list[str]
    latency_ms: int = Field(ge=0)
    token_usage: TokenUsageObservation
    prompt_versions: list[str]
    model_names: list[str]


class DeterministicCaseScores(BaseModel):
    """Rule metrics for a single case; None means the metric is not applicable."""

    model_config = ConfigDict(extra="forbid")

    retrieval_rank: int | None
    recall_at_3: float | None
    recall_at_5: float | None
    reciprocal_rank: float | None
    citation_validity: float | None
    evidence_coverage: float | None
    unsupported_claim_rate: float | None
    refusal_correctness: bool | None
    intent_accuracy: bool
    tool_selection_accuracy: bool
    tool_argument_accuracy: bool | None
    workflow_completion: bool
    prohibited_action: bool


class CaseEvaluationResult(BaseModel):
    """Raw observation, deterministic scores, and actionable failure reasons."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvaluationCategory
    observation: AgentObservation
    deterministic_scores: DeterministicCaseScores
    failures: list[str]


class MetricValue(BaseModel):
    """One named aggregate with its real denominator."""

    model_config = ConfigDict(extra="forbid")

    value: float | None
    sample_count: int = Field(ge=0)
    numerator: float | None = None


class SystemMetricSummary(BaseModel):
    """Operational aggregates kept separate from quality percentages."""

    model_config = ConfigDict(extra="forbid")

    latency_ms: MetricValue
    tool_error_rate: MetricValue
    average_steps: MetricValue
    token_usage: TokenUsageObservation
    average_total_tokens: MetricValue


class AggregateMetrics(BaseModel):
    """Required Retrieval, Generation, Agent, and System metrics."""

    model_config = ConfigDict(extra="forbid")

    retrieval: dict[str, MetricValue]
    generation: dict[str, MetricValue]
    agent: dict[str, MetricValue]
    system: SystemMetricSummary
