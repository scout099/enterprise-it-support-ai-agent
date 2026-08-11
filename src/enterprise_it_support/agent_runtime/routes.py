"""FastAPI routes for bounded Agent execution and trace inspection."""

from uuid import UUID

from fastapi import APIRouter, Query, Request
from psycopg import Error as PsycopgError
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.agent_runtime.persistence import (
    AgentRunNotFoundError,
    AgentRunRepository,
    StoredAgentRun,
)
from enterprise_it_support.agent_runtime.runtime import AgentRuntime
from enterprise_it_support.agent_runtime.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStepResponse,
    ToolExecutionResponse,
)
from enterprise_it_support.agent_runtime.state import AgentIntent, RiskLevel
from enterprise_it_support.interaction.errors import (
    ApplicationError,
    ServiceUnavailableError,
)
from enterprise_it_support.tools.persistence import (
    StoredToolExecution,
    ToolExecutionRepository,
)

router = APIRouter(prefix="/agent", tags=["agent"])


def _runtime(request: Request) -> AgentRuntime:
    runtime = request.app.state.agent_runtime
    if runtime is None:
        raise ServiceUnavailableError("Agent Runtime is not configured")
    return runtime


def _repository(request: Request) -> AgentRunRepository:
    repository = request.app.state.agent_run_repository
    if repository is None:
        raise ServiceUnavailableError("Agent trace service is not configured")
    return repository


@router.post("/runs", response_model=AgentRunResponse)
async def create_agent_run(payload: AgentRunRequest, request: Request) -> AgentRunResponse:
    """Execute one bounded graph and return its complete persisted node trace."""
    try:
        run = await _runtime(request).run(
            user_message=payload.user_message,
            user_role=payload.user_role,
            request_id=request.state.request_id,
            conversation_id=payload.conversation_id,
        )
    except (PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError("Agent Runtime is temporarily unavailable") from exception
    return agent_run_response(run, await load_tool_executions(request, run.id))


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: UUID,
    request: Request,
    user_role: str = Query(min_length=1, max_length=100),
) -> AgentRunResponse:
    """Read the latest state and ordered steps after local-role enforcement."""
    try:
        run = await _repository(request).get(run_id)
    except AgentRunNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="agent_run_not_found",
            message="Agent Run was not found",
        ) from exception
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError(
            "Agent trace service is temporarily unavailable"
        ) from exception
    if str(run.state["user_context"]["role"]) != user_role.strip():
        raise ApplicationError(
            status_code=403,
            code="agent_run_role_mismatch",
            message="Agent Run cannot be accessed with this role",
        )
    return agent_run_response(run, await load_tool_executions(request, run.id))


async def load_tool_executions(
    request: Request,
    run_id: UUID,
) -> tuple[StoredToolExecution, ...]:
    repository: ToolExecutionRepository | None = request.app.state.tool_execution_repository
    if repository is None:
        return ()
    try:
        return await repository.list_for_run(run_id)
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError(
            "Tool execution trace is temporarily unavailable"
        ) from exception


def agent_run_response(
    run: StoredAgentRun,
    tool_executions: tuple[StoredToolExecution, ...],
) -> AgentRunResponse:
    state = run.state
    return AgentRunResponse(
        run_id=run.id,
        request_id=run.request_id,
        conversation_id=run.conversation_id,
        status=run.status,
        intent=None if run.intent is None else AgentIntent(run.intent),
        intent_confidence=run.intent_confidence,
        risk_level=RiskLevel(run.risk_level),
        missing_information=state["missing_information"],
        reasoning_summary=state["reasoning_summary"],
        retrieved_evidence=state["retrieved_evidence"],
        planned_steps=state["planned_steps"],
        tool_results=state["tool_results"],
        tool_call_count=state["tool_call_count"],
        diagnostic_context=state["diagnostic_context"],
        escalation_reason=state["escalation_reason"],
        tool_executions=[
            ToolExecutionResponse(
                id=item.id,
                node_name=item.node_name,
                tool_name=item.tool_name,
                tool_version=item.tool_version,
                status=item.status,
                observation=item.observation,
                risk_level=item.risk_level,
                has_side_effect=item.has_side_effect,
                error_code=item.error_code,
                error_message=item.error_message,
                attempts=item.attempts,
                latency_ms=item.latency_ms,
                started_at=item.started_at,
                completed_at=item.completed_at,
            )
            for item in tool_executions
        ],
        classification_metadata=state["classification_metadata"],
        final_response=state["final_response"],
        error=state["error"],
        retry_count=state["retry_count"],
        node_count=state["node_count"],
        current_node=state["current_node"],
        governance_action=state.get("governance_action"),
        governance_risk_level=state.get("governance_risk_level"),
        governance_policy_decision=state.get("governance_policy_decision"),
        approval_request_id=(
            None
            if state.get("approval_request_id") is None
            else UUID(str(state["approval_request_id"]))
        ),
        approval_decision=state.get("approval_decision"),
        simulated_execution=state.get("simulated_execution"),
        started_at=run.started_at,
        completed_at=run.completed_at,
        steps=[
            AgentStepResponse(
                id=step.id,
                sequence_number=step.sequence_number,
                node_name=step.node_name,
                status=step.status,
                error_code=step.error_code,
                latency_ms=step.latency_ms,
                started_at=step.started_at,
                completed_at=step.completed_at,
            )
            for step in run.steps
        ],
    )
