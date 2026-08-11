"""Serializable LangGraph state and structured intent-classification contracts."""

from enum import StrEnum
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

INTENT_PROMPT_VERSION = "intent-classification-v1"
INTENT_SYSTEM_PROMPT = """Classify one enterprise IT support request.
Return only the requested JSON object. Choose exactly one allowed intent.
Use knowledge_question for requests asking what enterprise documentation says or how to follow a
known procedure. Use a diagnosis intent only when the user reports a problem to troubleshoot.
Use ticket_request when the user asks to create or update a support ticket.
Use unsupported_request for non-IT, unsafe, disallowed, or out-of-scope requests.
List only information that is necessary before routing. reasoning_summary must be a short decision
explanation, never hidden reasoning or chain-of-thought.
"""


class AgentIntent(StrEnum):
    """Allowlisted Phase 6 intents."""

    KNOWLEDGE_QUESTION = "knowledge_question"
    VPN_DIAGNOSIS = "vpn_diagnosis"
    OUTLOOK_DIAGNOSIS = "outlook_diagnosis"
    ACCOUNT_DIAGNOSIS = "account_diagnosis"
    TICKET_REQUEST = "ticket_request"
    UNSUPPORTED_REQUEST = "unsupported_request"


class RiskLevel(StrEnum):
    """Coarse risk supplied by classification and enforced by deterministic routing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentRunStatus(StrEnum):
    """Persisted lifecycle for one graph invocation."""

    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"
    FAILED = "failed"


class AgentStepStatus(StrEnum):
    """Persisted outcome for one node attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IntentClassification(BaseModel):
    """Strict model output accepted by the deterministic router."""

    model_config = ConfigDict(extra="forbid")

    intent: AgentIntent
    confidence: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    missing_information: list[str] = Field(max_length=10)
    reasoning_summary: str = Field(min_length=1, max_length=300)

    @field_validator("reasoning_summary")
    @classmethod
    def require_short_single_line_summary(cls, value: str) -> str:
        """Keep the persisted explanation to one compact routing decision."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Reasoning summary cannot be blank")
        if "\n" in normalized or "\r" in normalized:
            raise ValueError("Reasoning summary must be a single line")
        return normalized


class AgentState(TypedDict):
    """Checkpoint-safe state shared by every Agent Runtime node."""

    request_id: str
    run_id: str
    conversation_id: str | None
    user_message: str
    user_context: dict[str, Any]
    intent: str | None
    intent_confidence: float
    risk_level: str
    missing_information: list[str]
    reasoning_summary: str
    retrieved_evidence: list[dict[str, Any]]
    planned_steps: list[str]
    tool_results: list[dict[str, Any]]
    tool_call_count: int
    diagnostic_context: dict[str, Any]
    escalation_reason: str | None
    classification_metadata: dict[str, Any] | None
    final_response: dict[str, Any] | None
    error: dict[str, str] | None
    retry_count: int
    node_count: int
    current_node: str | None
    status: str
    governance_action: str | None
    governance_tool: str | None
    governance_target_resource: str | None
    governance_risk_level: str | None
    governance_policy_decision: str | None
    business_justification: str | None
    approval_request_id: str | None
    approval_decision: str | None
    simulated_execution: dict[str, Any] | None


def initial_agent_state(
    *,
    run_id: str,
    request_id: str,
    conversation_id: str | None,
    user_message: str,
    user_role: str,
    actor_id: str | None = None,
    idempotency_key: str | None = None,
    business_justification: str | None = None,
) -> AgentState:
    """Create a complete initial state so checkpoints never depend on implicit defaults."""
    return AgentState(
        request_id=request_id,
        run_id=run_id,
        conversation_id=conversation_id,
        user_message=user_message,
        user_context={
            "role": user_role,
            "actor_id": actor_id,
            "idempotency_key": idempotency_key,
        },
        intent=None,
        intent_confidence=0.0,
        risk_level=RiskLevel.LOW.value,
        missing_information=[],
        reasoning_summary="",
        retrieved_evidence=[],
        planned_steps=[],
        tool_results=[],
        tool_call_count=0,
        diagnostic_context={},
        escalation_reason=None,
        classification_metadata=None,
        final_response=None,
        error=None,
        retry_count=0,
        node_count=0,
        current_node=None,
        status=AgentRunStatus.RUNNING.value,
        governance_action=None,
        governance_tool=None,
        governance_target_resource=None,
        governance_risk_level=None,
        governance_policy_decision=None,
        business_justification=business_justification,
        approval_request_id=None,
        approval_decision=None,
        simulated_execution=None,
    )
