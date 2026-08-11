"""Execute the real local Agent surface and collect provider-neutral raw observations."""

from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel

from enterprise_it_support.conversation.repository import ConversationRepository, TurnStatus
from enterprise_it_support.evaluation.dataset import EvaluationCase, EvaluationDataset
from enterprise_it_support.evaluation.judge import EvaluationJudge, JudgeCaseResult
from enterprise_it_support.evaluation.metrics import aggregate_metrics, evaluate_case
from enterprise_it_support.evaluation.models import (
    AgentObservation,
    AggregateMetrics,
    CaseEvaluationResult,
    TokenUsageObservation,
    ToolCallObservation,
)
from enterprise_it_support.intelligence.model_gateway import (
    ModelCallMetadata,
    ModelGateway,
    ModelGatewayError,
    ModelMessage,
    StructuredModelResponse,
)
from enterprise_it_support.tools.contracts import ToolExecutionStatus
from enterprise_it_support.tools.persistence import ToolExecutionRepository

_DANGEROUS_TOOL_TOKENS = {
    "shell": "shell_execution",
    "python": "python_execution",
    "sql": "sql_execution",
}


class EvaluationSubject(Protocol):
    """Narrow seam that permits deterministic full-run tests without external APIs."""

    async def execute(self, case: EvaluationCase) -> AgentObservation: ...


@dataclass(frozen=True)
class EvaluationExecution:
    """Complete deterministic and optional advisory result for one dataset run."""

    metrics: AggregateMetrics
    category_metrics: dict[str, AggregateMetrics]
    cases: tuple[CaseEvaluationResult, ...]
    judge_results: tuple[JudgeCaseResult, ...]


class TrackingModelGateway:
    """Record metadata around an existing gateway without changing its behavior."""

    def __init__(self, wrapped: ModelGateway) -> None:
        self._wrapped = wrapped
        self.records: list[ModelCallMetadata] = []

    @property
    def model_name(self) -> str:
        return self._wrapped.model_name

    def mark(self) -> int:
        return len(self.records)

    def since(self, marker: int) -> tuple[ModelCallMetadata, ...]:
        return tuple(self.records[marker:])

    async def generate_structured_response(
        self,
        *,
        messages: Sequence[ModelMessage],
        response_schema: type[BaseModel],
        prompt_version: str,
    ) -> StructuredModelResponse[Any]:
        try:
            response = await self._wrapped.generate_structured_response(
                messages=messages,
                response_schema=response_schema,
                prompt_version=prompt_version,
            )
        except ModelGatewayError as exception:
            if exception.metadata is not None:
                self.records.append(exception.metadata)
            raise
        self.records.append(response.metadata)
        return response


class LocalAgentEvaluationSubject:
    """Drive `/agent/respond` and read existing trace repositories for exact observations."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        model_gateway: TrackingModelGateway,
        conversation_repository: ConversationRepository,
        tool_repository: ToolExecutionRepository,
        execution_nonce: str | None = None,
    ) -> None:
        self._client = client
        self._model_gateway = model_gateway
        self._conversations = conversation_repository
        self._tools = tool_repository
        self._nonce = execution_nonce or uuid4().hex[:12]

    async def execute(self, case: EvaluationCase) -> AgentObservation:
        marker = self._model_gateway.mark()
        started = monotonic()
        response = await self._client.post(
            "/agent/respond",
            json={
                "user_message": case.user_query,
                "actor_id": case.user_context.actor_id,
                "user_role": case.user_context.user_role,
                "idempotency_key": f"eval-{self._nonce}-{case.case_id}",
                "business_justification": case.user_context.business_justification,
            },
        )
        latency_ms = max(0, int((monotonic() - started) * 1000))
        metadata = self._model_gateway.since(marker)
        if response.status_code != 200:
            return _http_failure_observation(case, response, latency_ms, metadata)

        body = response.json()
        run = body["run"]
        run_id = UUID(run["run_id"])
        stored_tools = await self._tools.list_for_run(run_id)
        tool_calls = [
            ToolCallObservation(
                tool_name=tool.tool_name,
                arguments=tool.input_arguments,
                status=tool.status.value,
                error_code=tool.error_code,
                latency_ms=tool.latency_ms,
            )
            for tool in stored_tools
        ]

        refused: bool | None = None
        if run["conversation_id"] is not None:
            conversation = await self._conversations.get(UUID(run["conversation_id"]))
            assistant = next(
                (
                    message
                    for message in reversed(conversation.messages)
                    if message.role == "assistant"
                ),
                None,
            )
            if assistant is not None and assistant.status is not None:
                refused = assistant.status is TurnStatus.REFUSED

        final_response = run["final_response"]
        citations = [] if final_response is None else final_response.get("citations", [])
        retrieved = run["retrieved_evidence"]
        pending = body.get("pending_confirmation")
        actual_actions = [
            action
            for tool in stored_tools
            for action in observed_tool_actions(
                tool_name=tool.tool_name,
                status=tool.status,
                has_side_effect=tool.has_side_effect,
            )
        ]
        if any(tool.status.value == "not_found" for tool in stored_tools):
            actual_actions.append("unregistered_tool_call")
        if pending is not None:
            actual_actions.append(f"proposed:{pending['action']}")
        simulated = run.get("simulated_execution") or {}
        if simulated.get("external_system_modified") is True:
            actual_actions.append("external_system_modified")

        final_status = (
            "confirmation_required"
            if pending is not None and pending["status"] == "pending"
            else run["status"]
        )
        actual_intent = "governance_request" if run.get("governance_action") else run.get("intent")
        if (
            refused is None
            and actual_intent == "unsupported_request"
            and final_status == "escalated"
        ):
            refused = True
        claims = []
        if case.category.value == "knowledge_question" and refused is False and final_response:
            answer = str(final_response.get("answer", "")).strip()
            if answer:
                claims.append(answer)

        return AgentObservation(
            case_id=case.case_id,
            category=case.category,
            actual_intent=actual_intent,
            retrieved_document_titles=_deduplicate(
                str(item["document_title"]) for item in retrieved
            ),
            retrieved_chunk_ids=[str(item["chunk_id"]) for item in retrieved],
            evidence_texts=[str(item["content"]) for item in retrieved],
            citation_document_titles=[str(item["document_title"]) for item in citations],
            citation_chunk_ids=[str(item["chunk_id"]) for item in citations],
            tool_calls=tool_calls,
            final_status=final_status,
            final_response=final_response,
            refused=refused,
            claims=claims,
            actual_actions=_deduplicate(actual_actions),
            steps=[str(step["node_name"]) for step in run["steps"]],
            latency_ms=latency_ms,
            token_usage=_token_usage(metadata),
            prompt_versions=_deduplicate(item.prompt_version for item in metadata),
            model_names=_deduplicate(item.resolved_model for item in metadata),
        )


async def run_evaluation(
    dataset: EvaluationDataset,
    subject: EvaluationSubject,
    *,
    judge: EvaluationJudge | None = None,
) -> EvaluationExecution:
    """Run every case independently and aggregate deterministic results."""
    case_results = []
    judge_results = []
    for case in dataset.cases:
        observation = await subject.execute(case)
        case_results.append(evaluate_case(case, observation))
        if judge is not None:
            judge_results.append(await judge.score(case, observation))

    frozen_results = tuple(case_results)
    categories = {case.category.value for case in dataset.cases}
    return EvaluationExecution(
        metrics=aggregate_metrics(frozen_results),
        category_metrics={
            category: aggregate_metrics(
                result for result in frozen_results if result.category.value == category
            )
            for category in sorted(categories)
        },
        cases=frozen_results,
        judge_results=tuple(judge_results),
    )


def _http_failure_observation(
    case: EvaluationCase,
    response: httpx.Response,
    latency_ms: int,
    metadata: tuple[ModelCallMetadata, ...],
) -> AgentObservation:
    try:
        error = response.json()
    except ValueError:
        error = {"status_code": response.status_code, "detail": "non_json_response"}
    return AgentObservation(
        case_id=case.case_id,
        category=case.category,
        actual_intent=None,
        retrieved_document_titles=[],
        retrieved_chunk_ids=[],
        evidence_texts=[],
        citation_document_titles=[],
        citation_chunk_ids=[],
        tool_calls=[],
        final_status=f"http_error_{response.status_code}",
        final_response=error,
        refused=None,
        claims=[],
        actual_actions=[],
        steps=[],
        latency_ms=latency_ms,
        token_usage=_token_usage(metadata),
        prompt_versions=_deduplicate(item.prompt_version for item in metadata),
        model_names=_deduplicate(item.resolved_model for item in metadata),
    )


def _token_usage(metadata: tuple[ModelCallMetadata, ...]) -> TokenUsageObservation:
    return TokenUsageObservation(
        input_tokens=sum(item.usage.input_tokens for item in metadata),
        output_tokens=sum(item.usage.output_tokens for item in metadata),
        total_tokens=sum(item.usage.total_tokens for item in metadata),
        cached_tokens=sum(item.usage.cached_tokens for item in metadata),
        reasoning_tokens=sum(item.usage.reasoning_tokens for item in metadata),
        model_calls=len(metadata),
    )


def observed_tool_actions(
    *,
    tool_name: str,
    status: ToolExecutionStatus,
    has_side_effect: bool,
) -> tuple[str, ...]:
    """Map audited tools into the canonical safety-action vocabulary."""
    normalized_name = tool_name.casefold()
    actions = [tool_name, f"tool:{tool_name}"]
    actions.extend(
        action for token, action in _DANGEROUS_TOOL_TOKENS.items() if token in normalized_name
    )
    if has_side_effect and status is ToolExecutionStatus.SUCCEEDED:
        actions.extend(
            (f"executed:{tool_name}", "side_effect_executed", "external_system_modified")
        )
    return tuple(dict.fromkeys(actions))


def _deduplicate(values: Sequence[str] | Any) -> list[str]:
    return list(dict.fromkeys(values))
