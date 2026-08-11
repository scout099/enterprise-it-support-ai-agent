"""Approver-only HTTP routes for local simulated approval."""

from uuid import UUID

from fastapi import APIRouter, Query, Request
from psycopg import Error as PsycopgError
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.agent_runtime.persistence import StoredAgentRun
from enterprise_it_support.agent_runtime.routes import (
    agent_run_response,
    load_tool_executions,
)
from enterprise_it_support.agent_runtime.runtime import AgentRuntime
from enterprise_it_support.agent_runtime.state import AgentRunStatus
from enterprise_it_support.governance.domain import (
    ApprovalAlreadyDecidedError,
    ApprovalConflictError,
    ApprovalDecisionValue,
    ApprovalRequestNotFoundError,
    ApprovalStatus,
    GovernanceAccessDeniedError,
    LocalUserNotFoundError,
    StoredApprovalRequest,
)
from enterprise_it_support.governance.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalOutcomeResponse,
    ApprovalRequestResponse,
    PendingApprovalListResponse,
)
from enterprise_it_support.governance.service import GovernanceService
from enterprise_it_support.interaction.errors import ApplicationError, ServiceUnavailableError

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _service(request: Request) -> GovernanceService:
    service: GovernanceService | None = request.app.state.governance_service
    if service is None:
        raise ServiceUnavailableError("Governance service is not configured")
    return service


def _runtime(request: Request) -> AgentRuntime:
    runtime: AgentRuntime | None = request.app.state.agent_runtime
    if runtime is None:
        raise ServiceUnavailableError("Agent Runtime is not configured")
    return runtime


@router.get("/pending", response_model=PendingApprovalListResponse)
async def list_pending_approvals(
    request: Request,
    actor_id: str = Query(min_length=1, max_length=128),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
) -> PendingApprovalListResponse:
    """Return a bounded pending queue only to an RBAC-authorized approver."""
    try:
        items = await _service(request).list_pending(
            actor_id=actor_id.strip(),
            limit=limit,
            offset=offset,
            request_id=request.state.request_id,
        )
    except (GovernanceAccessDeniedError, LocalUserNotFoundError) as exception:
        raise ApplicationError(
            status_code=403,
            code="approval_access_denied",
            message="Pending approvals require approver authority",
        ) from exception
    except (PsycopgError, SQLAlchemyError) as exception:
        raise ServiceUnavailableError("Approvals are temporarily unavailable") from exception
    return PendingApprovalListResponse(
        items=[_approval_response(item) for item in items],
        limit=limit,
        offset=offset,
    )


@router.post("/{approval_id}/approve", response_model=ApprovalOutcomeResponse)
async def approve(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
) -> ApprovalOutcomeResponse:
    return await _decide(
        approval_id=approval_id,
        payload=payload,
        request=request,
        decision=ApprovalDecisionValue.APPROVE,
    )


@router.post("/{approval_id}/reject", response_model=ApprovalOutcomeResponse)
async def reject(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
) -> ApprovalOutcomeResponse:
    return await _decide(
        approval_id=approval_id,
        payload=payload,
        request=request,
        decision=ApprovalDecisionValue.REJECT,
    )


async def _decide(
    *,
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
    decision: ApprovalDecisionValue,
) -> ApprovalOutcomeResponse:
    try:
        service = _service(request)
        runtime = _runtime(request)
        async with service.decision_lock(approval_id):
            approval = await service.decide(
                approval_request_id=approval_id,
                actor_id=payload.actor_id,
                decision=decision,
                rationale=payload.rationale,
                request_id=request.state.request_id,
            )
            try:
                run = await runtime.resume(
                    approval.source_agent_run_id,
                    resume_value={
                        "approval_request_id": str(approval.id),
                        "decision": decision.value,
                    },
                )
            except (PsycopgError, SQLAlchemyError, RuntimeError) as exception:
                await service.audit_resume_failure(
                    approval_request_id=approval.id,
                    source_agent_run_id=approval.source_agent_run_id,
                    decision=decision,
                    request_id=request.state.request_id,
                )
                raise ServiceUnavailableError(
                    "Approval could not be completed safely"
                ) from exception
            refreshed = await service.get(approval.id)
            _ensure_resume_completed(
                approval=refreshed,
                run=run,
                decision=decision,
            )
            tool_executions = await load_tool_executions(request, run.id)
            refreshed = await service.mark_resumed(
                approval_request_id=approval.id,
                decision=decision,
                request_id=request.state.request_id,
            )
    except ApprovalRequestNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code=exception.code,
            message="Approval request was not found",
        ) from exception
    except (GovernanceAccessDeniedError, LocalUserNotFoundError) as exception:
        raise ApplicationError(
            status_code=403,
            code="approval_access_denied",
            message="This actor cannot decide the approval request",
        ) from exception
    except ApprovalAlreadyDecidedError as exception:
        raise ApplicationError(
            status_code=409,
            code=exception.code,
            message="Approval request already has a decision",
        ) from exception
    except ApprovalConflictError as exception:
        raise ApplicationError(
            status_code=409,
            code=exception.code,
            message="Approval request is not in a resumable state",
        ) from exception
    except (PsycopgError, SQLAlchemyError, RuntimeError) as exception:
        raise ServiceUnavailableError("Approval could not be completed safely") from exception
    return ApprovalOutcomeResponse(
        approval=_approval_response(refreshed),
        run=agent_run_response(run, tool_executions),
    )


def _approval_response(item: StoredApprovalRequest) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=item.id,
        requester_user_id=item.requester_user_id,
        requester_external_id=item.requester_external_id,
        action=item.action,
        tool=item.tool,
        target_resource=item.target_resource,
        risk_level=item.risk_level,
        business_justification=item.business_justification,
        policy_decision=item.policy_decision,
        status=item.status,
        idempotency_key=item.idempotency_key,
        source_agent_run_id=item.source_agent_run_id,
        checkpoint_node=item.checkpoint_node,
        simulated_result=item.simulated_result,
        created_at=item.created_at,
        decided_at=item.decided_at,
        executed_at=item.executed_at,
        resumed_at=item.resumed_at,
        decision=(
            None
            if item.decision is None
            else ApprovalDecisionResponse(
                id=item.decision.id,
                approval_request_id=item.decision.approval_request_id,
                approver_user_id=item.decision.approver_user_id,
                approver_external_id=item.decision.approver_external_id,
                decision=item.decision.decision,
                rationale=item.decision.rationale,
                decided_at=item.decision.decided_at,
            )
        ),
    )


def _ensure_resume_completed(
    *,
    approval: StoredApprovalRequest,
    run: StoredAgentRun,
    decision: ApprovalDecisionValue,
) -> None:
    expected_status = (
        ApprovalStatus.EXECUTED
        if decision is ApprovalDecisionValue.APPROVE
        else ApprovalStatus.REJECTED
    )
    if (
        run.id != approval.source_agent_run_id
        or run.status is not AgentRunStatus.COMPLETED
        or run.state.get("approval_request_id") != str(approval.id)
        or run.state.get("approval_decision") != decision.value
        or approval.status is not expected_status
    ):
        raise RuntimeError("Approval checkpoint did not reach the expected terminal state")
