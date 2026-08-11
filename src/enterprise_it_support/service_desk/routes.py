"""Phase 8 HTTP routes for confirmed local service-desk actions."""

import json

from fastapi import APIRouter, Query, Request
from psycopg import Error as PsycopgError
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.agent_runtime.persistence import StoredAgentRun
from enterprise_it_support.agent_runtime.routes import (
    agent_run_response,
    load_tool_executions,
)
from enterprise_it_support.agent_runtime.runtime import AgentRuntime
from enterprise_it_support.agent_runtime.state import AgentIntent, AgentRunStatus
from enterprise_it_support.interaction.errors import ApplicationError, ServiceUnavailableError
from enterprise_it_support.service_desk.domain import (
    ConfirmationAccessDeniedError,
    ConfirmationNotFoundError,
    ConfirmationStateError,
    IdempotencyConflictError,
    StoredPendingConfirmation,
)
from enterprise_it_support.service_desk.persistence import AuditEventRepository
from enterprise_it_support.service_desk.schemas import (
    AgentCancelRequest,
    AgentConfirmRequest,
    AgentRespondRequest,
    AgentRespondResponse,
    AuditEventListResponse,
    AuditEventResponse,
    PendingConfirmationResponse,
    TicketResponse,
)
from enterprise_it_support.service_desk.service import (
    ServiceDeskExecutionError,
    ServiceDeskService,
)
from enterprise_it_support.service_desk.tools import service_desk_permissions
from enterprise_it_support.tools.gateway import ToolActionValidationError

router = APIRouter(tags=["service-desk"])


def _runtime(request: Request) -> AgentRuntime:
    runtime: AgentRuntime | None = request.app.state.agent_runtime
    if runtime is None:
        raise ServiceUnavailableError("Agent Runtime is not configured")
    return runtime


def _service(request: Request) -> ServiceDeskService:
    service: ServiceDeskService | None = request.app.state.service_desk_service
    if service is None:
        raise ServiceUnavailableError("Local service desk is not configured")
    return service


def _audit_repository(request: Request) -> AuditEventRepository:
    repository: AuditEventRepository | None = request.app.state.audit_event_repository
    if repository is None:
        raise ServiceUnavailableError("Audit event service is not configured")
    return repository


@router.post("/agent/respond", response_model=AgentRespondResponse)
async def respond(payload: AgentRespondRequest, request: Request) -> AgentRespondResponse:
    """Run the Agent and prepare, but never execute, any R1/R3 action."""
    try:
        run = await _runtime(request).run(
            user_message=payload.user_message,
            user_role=payload.user_role,
            request_id=request.state.request_id,
            conversation_id=payload.conversation_id,
            actor_id=payload.actor_id,
            idempotency_key=payload.idempotency_key,
            business_justification=payload.business_justification,
        )
        pending = await _plan_action(
            service=_service(request),
            payload=payload,
            run=run,
            request_id=request.state.request_id,
        )
        run_response = agent_run_response(
            run,
            await load_tool_executions(request, run.id),
        )
    except ToolActionValidationError as exception:
        status_code = 403 if exception.code == "tool_permission_denied" else 422
        raise ApplicationError(
            status_code=status_code,
            code=exception.code,
            message=str(exception),
        ) from exception
    except IdempotencyConflictError as exception:
        raise ApplicationError(
            status_code=409,
            code="idempotency_conflict",
            message="Idempotency key was reused with different action parameters",
        ) from exception
    except (PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError(
            "Agent or local service desk is temporarily unavailable"
        ) from exception
    return AgentRespondResponse(
        run=run_response,
        pending_confirmation=(None if pending is None else _pending_response(pending)),
    )


@router.post("/agent/confirm", response_model=PendingConfirmationResponse)
async def confirm(
    payload: AgentConfirmRequest,
    request: Request,
) -> PendingConfirmationResponse:
    """Claim, revalidate, and execute exactly one R1 pending action."""
    try:
        pending = await _service(request).confirm(
            confirmation_id=payload.confirmation_id,
            actor_id=payload.actor_id,
            actor_role=payload.user_role,
            request_id=request.state.request_id,
        )
    except ConfirmationNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="confirmation_not_found",
            message="Pending confirmation was not found",
        ) from exception
    except ConfirmationAccessDeniedError as exception:
        raise ApplicationError(
            status_code=403,
            code="confirmation_access_denied",
            message="Pending confirmation cannot be accessed by this actor",
        ) from exception
    except ConfirmationStateError as exception:
        raise ApplicationError(
            status_code=409,
            code="confirmation_not_executable",
            message="Pending confirmation is not executable",
        ) from exception
    except (ServiceDeskExecutionError, PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError(
            "Confirmed action could not be completed safely"
        ) from exception
    return _pending_response(pending)


@router.post("/agent/cancel", response_model=PendingConfirmationResponse)
async def cancel(
    payload: AgentCancelRequest,
    request: Request,
) -> PendingConfirmationResponse:
    """Cancel an owned R1 proposal before it is executed."""
    try:
        pending = await _service(request).cancel(
            confirmation_id=payload.confirmation_id,
            actor_id=payload.actor_id,
            actor_role=payload.user_role,
            request_id=request.state.request_id,
        )
    except ConfirmationNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="confirmation_not_found",
            message="Pending confirmation was not found",
        ) from exception
    except ConfirmationAccessDeniedError as exception:
        raise ApplicationError(
            status_code=403,
            code="confirmation_access_denied",
            message="Pending confirmation cannot be accessed by this actor",
        ) from exception
    except ConfirmationStateError as exception:
        raise ApplicationError(
            status_code=409,
            code="confirmation_not_cancellable",
            message="Pending confirmation is not cancellable",
        ) from exception
    except (PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError("Pending action could not be cancelled safely") from exception
    return _pending_response(pending)


@router.get("/tickets/{ticket_number}", response_model=TicketResponse)
async def get_ticket(
    ticket_number: str,
    request: Request,
    actor_id: str = Query(min_length=1, max_length=128),
    user_role: str = Query(min_length=1, max_length=100),
) -> TicketResponse:
    """Execute the R0 get-ticket-status tool with resource authorization."""
    try:
        result = await _service(request).get_ticket_status(
            ticket_number=ticket_number,
            actor_id=actor_id.strip(),
            actor_role=user_role.strip(),
            request_id=request.state.request_id,
        )
    except ServiceDeskExecutionError as exception:
        code = exception.code
        status_code = {
            "tool_permission_denied": 403,
            "tool_resource_permission_denied": 403,
            "tool_not_found": 404,
            "tool_resource_not_found": 404,
        }.get(code, 503)
        raise ApplicationError(
            status_code=status_code,
            code=code,
            message=(
                "Ticket is not accessible"
                if status_code == 403
                else "Ticket was not found"
                if status_code == 404
                else "Ticket status is temporarily unavailable"
            ),
        ) from exception
    except (PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError("Ticket status is temporarily unavailable") from exception
    return TicketResponse.model_validate(result)


@router.get("/audit/events", response_model=AuditEventListResponse)
async def list_audit_events(
    request: Request,
    actor_id: str = Query(min_length=1, max_length=128),
    user_role: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
) -> AuditEventListResponse:
    """Return a bounded audit page to local support/maintainer roles."""
    _ = actor_id
    permissions = service_desk_permissions().get(user_role.strip(), frozenset())
    if "audit:read" not in permissions:
        raise ApplicationError(
            status_code=403,
            code="audit_access_denied",
            message="Audit events require local support authority",
        )
    try:
        events = await _audit_repository(request).list_recent(
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError("Audit events are temporarily unavailable") from exception
    return AuditEventListResponse(
        items=[
            AuditEventResponse(
                id=event.id,
                actor=event.actor,
                action=event.action,
                target=event.target,
                parameters_summary=event.parameters_summary,
                policy_decision=event.policy_decision,
                execution_result=event.execution_result,
                request_id=event.request_id,
                created_at=event.created_at,
            )
            for event in events
        ],
        limit=limit,
        offset=offset,
    )


async def _plan_action(
    *,
    service: ServiceDeskService,
    payload: AgentRespondRequest,
    run: StoredAgentRun,
    request_id: str,
) -> StoredPendingConfirmation | None:
    if payload.ticket_number is not None:
        return await service.propose_add_comment(
            actor_id=payload.actor_id,
            actor_role=payload.user_role,
            request_id=request_id,
            idempotency_key=payload.idempotency_key,
            ticket_number=payload.ticket_number,
            body=payload.user_message,
            source_agent_run_id=run.id,
        )
    high_risk_action = _high_risk_action(payload.user_message)
    if high_risk_action is not None:
        return await service.create_approval_request(
            actor_id=payload.actor_id,
            actor_role=payload.user_role,
            request_id=request_id,
            idempotency_key=payload.idempotency_key,
            action=high_risk_action,
            target="current_account",
            source_agent_run_id=run.id,
        )
    if run.intent == AgentIntent.TICKET_REQUEST.value or run.status in {
        AgentRunStatus.ESCALATED,
        AgentRunStatus.FAILED,
    }:
        category = _ticket_category(run, payload.user_message)
        return await service.propose_create_ticket(
            actor_id=payload.actor_id,
            actor_role=payload.user_role,
            request_id=request_id,
            idempotency_key=payload.idempotency_key,
            title=f"{category.upper()} support request: {payload.user_message}"[:300],
            description=payload.user_message,
            category=category,
            priority=(
                "high"
                if run.status in {AgentRunStatus.ESCALATED, AgentRunStatus.FAILED}
                else "medium"
            ),
            source_conversation_id=run.conversation_id,
            source_agent_run_id=run.id,
            diagnosis_summary=_diagnosis_context(run),
        )
    return None


def _diagnosis_context(run: StoredAgentRun) -> str:
    state = run.state
    context = {
        "intent": run.intent,
        "run_status": run.status.value,
        "diagnosis": (state["final_response"] or {}).get("diagnosis", []),
        "tool_results": state["tool_results"],
        "escalation_reason": state["escalation_reason"],
        "error": state["error"],
    }
    return json.dumps(context, ensure_ascii=False, sort_keys=True)[:5000]


def _ticket_category(run: StoredAgentRun, message: str) -> str:
    intent = run.intent or ""
    for category in ("vpn", "outlook", "account"):
        if intent.startswith(category) or category in message.casefold():
            return category
    return "other"


def _high_risk_action(message: str) -> str | None:
    normalized = message.casefold()
    reset_terms = ("reset password", "重置密码")
    permission_terms = (
        "grant access",
        "change permission",
        "modify permission",
        "修改权限",
        "授予权限",
    )
    if any(term in normalized for term in reset_terms):
        return "reset_password"
    if any(term in normalized for term in permission_terms):
        return "modify_permissions"
    return None


def _pending_response(
    pending: StoredPendingConfirmation,
) -> PendingConfirmationResponse:
    return PendingConfirmationResponse(
        id=pending.id,
        action=pending.action,
        risk_level=pending.risk_level,
        status=pending.status,
        parameters=pending.parameters,
        parameters_summary=pending.parameters_summary,
        impact_summary=pending.impact_summary,
        idempotency_key=pending.idempotency_key,
        source_agent_run_id=pending.source_agent_run_id,
        source_conversation_id=pending.source_conversation_id,
        result=pending.result,
        error_code=pending.error_code,
        created_at=pending.created_at,
        confirmed_at=pending.confirmed_at,
        executed_at=pending.executed_at,
        cancelled_at=pending.cancelled_at,
    )
