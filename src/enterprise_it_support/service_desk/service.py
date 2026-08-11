"""Application service for proposals, confirmations, local tickets, and audit."""

import hashlib
import json
from typing import Any
from uuid import UUID

from enterprise_it_support.service_desk.domain import (
    ActionRisk,
    AuditEventCreate,
    ConfirmationAccessDeniedError,
    ConfirmationStateError,
    ConfirmationStatus,
    PendingConfirmationCreate,
    PolicyDecision,
    StoredPendingConfirmation,
    StoredTicket,
)
from enterprise_it_support.service_desk.persistence import (
    AuditEventRepository,
    PendingConfirmationRepository,
    TicketRepository,
)
from enterprise_it_support.tools.contracts import (
    ToolExecutionContext,
    ToolExecutionRequest,
)
from enterprise_it_support.tools.gateway import (
    ToolActionValidationError,
    ToolAuditUnavailableError,
    ToolExecutionGateway,
)


class ServiceDeskExecutionError(RuntimeError):
    """A confirmed action failed without exposing Adapter exception detail."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


class ServiceDeskService:
    """Coordinate validation, confirmation lifecycle, tools, and sanitized audit."""

    def __init__(
        self,
        *,
        gateway: ToolExecutionGateway,
        confirmations: PendingConfirmationRepository,
        tickets: TicketRepository,
        audit_events: AuditEventRepository,
    ) -> None:
        self._gateway = gateway
        self._confirmations = confirmations
        self._tickets = tickets
        self._audit_events = audit_events

    async def propose_create_ticket(
        self,
        *,
        actor_id: str,
        actor_role: str,
        request_id: str,
        idempotency_key: str,
        title: str,
        description: str,
        category: str,
        priority: str,
        source_conversation_id: UUID | None,
        source_agent_run_id: UUID | None,
        diagnosis_summary: str,
    ) -> StoredPendingConfirmation:
        arguments = {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "requester_id": actor_id,
            "assigned_to": None,
            "source_conversation_id": (
                None if source_conversation_id is None else str(source_conversation_id)
            ),
            "source_agent_run_id": (
                None if source_agent_run_id is None else str(source_agent_run_id)
            ),
            "diagnosis_summary": diagnosis_summary,
            "idempotency_key": idempotency_key,
        }
        summary = {
            "title_length": len(title),
            "description_length": len(description),
            "category": category,
            "priority": priority,
            "requester_id": actor_id,
            "diagnosis_summary_length": len(diagnosis_summary),
        }
        return await self._propose_r1(
            actor_id=actor_id,
            actor_role=actor_role,
            request_id=request_id,
            action="create_ticket",
            arguments=arguments,
            parameters_summary=summary,
            impact_summary="确认后将在本地 PostgreSQL 创建一条 IT 工单。",
            idempotency_key=idempotency_key,
            source_agent_run_id=source_agent_run_id,
            source_conversation_id=source_conversation_id,
        )

    async def propose_add_comment(
        self,
        *,
        actor_id: str,
        actor_role: str,
        request_id: str,
        idempotency_key: str,
        ticket_number: str,
        body: str,
        source_agent_run_id: UUID | None = None,
    ) -> StoredPendingConfirmation:
        return await self._propose_r1(
            actor_id=actor_id,
            actor_role=actor_role,
            request_id=request_id,
            action="add_ticket_comment",
            arguments={
                "ticket_number": ticket_number,
                "body": body,
                "author_id": actor_id,
                "idempotency_key": idempotency_key,
            },
            parameters_summary={
                "ticket_number": ticket_number,
                "comment_length": len(body),
                "author_id": actor_id,
            },
            impact_summary=f"确认后将向本地工单 {ticket_number} 追加一条评论。",
            idempotency_key=idempotency_key,
            source_agent_run_id=source_agent_run_id,
            source_conversation_id=None,
        )

    async def create_approval_request(
        self,
        *,
        actor_id: str,
        actor_role: str,
        request_id: str,
        idempotency_key: str,
        action: str,
        target: str,
        source_agent_run_id: UUID | None,
    ) -> StoredPendingConfirmation:
        parameters = {"target": target}
        return await self._confirmations.create(
            PendingConfirmationCreate(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                risk_level=ActionRisk.R3,
                status=ConfirmationStatus.APPROVAL_REQUIRED,
                parameters=parameters,
                parameters_summary={"target": target[:128]},
                impact_summary=("该 R3 请求只记录审批申请; 当前系统不会执行权限、密码或账号修改。"),
                idempotency_key=idempotency_key,
                request_fingerprint=_fingerprint(parameters),
                source_agent_run_id=source_agent_run_id,
                source_conversation_id=None,
            ),
            request_id=request_id,
        )

    async def confirm(
        self,
        *,
        confirmation_id: UUID,
        actor_id: str,
        actor_role: str,
        request_id: str,
    ) -> StoredPendingConfirmation:
        try:
            pending = await self._confirmations.claim(
                confirmation_id,
                actor_id=actor_id,
                actor_role=actor_role,
            )
        except (ConfirmationAccessDeniedError, ConfirmationStateError):
            await self._audit_events.append(
                AuditEventCreate(
                    actor=actor_id,
                    action="confirm_action",
                    target=f"pending_confirmation:{confirmation_id}",
                    parameters_summary={},
                    policy_decision=PolicyDecision.DENY,
                    execution_result="not_executed",
                    request_id=request_id,
                )
            )
            raise
        if pending.status is ConfirmationStatus.EXECUTED:
            await self._audit_events.append(
                AuditEventCreate(
                    actor=actor_id,
                    action=pending.action,
                    target=f"pending_confirmation:{pending.id}",
                    parameters_summary=pending.parameters_summary,
                    policy_decision=PolicyDecision.ALLOW,
                    execution_result="idempotent_replay",
                    request_id=request_id,
                )
            )
            return pending

        try:
            result = await self._gateway.execute(
                ToolExecutionRequest(
                    tool_name=pending.action,
                    arguments=pending.parameters,
                    context=ToolExecutionContext(
                        run_id=pending.source_agent_run_id,
                        request_id=request_id,
                        node_name="confirm_action",
                        user_role=actor_role,
                        actor_id=actor_id,
                        pending_confirmation_id=pending.id,
                        idempotency_key=pending.idempotency_key,
                    ),
                )
            )
        except ToolAuditUnavailableError as exception:
            if (
                exception.result is not None
                and exception.result.succeeded
                and exception.result.observation is not None
            ):
                return await self._confirmations.complete(
                    pending.id,
                    exception.result.observation,
                )
            await self._confirmations.fail(pending.id, "tool_audit_unavailable")
            raise ServiceDeskExecutionError(
                "tool_audit_unavailable",
                "Confirmed action audit storage is unavailable",
            ) from exception

        if not result.succeeded or result.observation is None:
            error_code = "tool_failed" if result.error is None else result.error.code
            failed = await self._confirmations.fail(pending.id, error_code)
            await self._audit_events.append(
                AuditEventCreate(
                    actor=actor_id,
                    action=pending.action,
                    target=f"pending_confirmation:{pending.id}",
                    parameters_summary=pending.parameters_summary,
                    policy_decision=PolicyDecision.ALLOW,
                    execution_result=f"failed:{error_code}",
                    request_id=request_id,
                )
            )
            return failed

        completed = await self._confirmations.complete(
            pending.id,
            result.observation,
        )
        return completed

    async def get_ticket_status(
        self,
        *,
        ticket_number: str,
        actor_id: str,
        actor_role: str,
        request_id: str,
        run_id: UUID | None = None,
    ) -> dict[str, Any]:
        try:
            result = await self._gateway.execute(
                ToolExecutionRequest(
                    tool_name="get_ticket_status",
                    arguments={"ticket_number": ticket_number},
                    context=ToolExecutionContext(
                        run_id=run_id,
                        request_id=request_id,
                        node_name="get_ticket_status",
                        user_role=actor_role,
                        actor_id=actor_id,
                    ),
                )
            )
        except ToolAuditUnavailableError as exception:
            raise ServiceDeskExecutionError("tool_audit_unavailable") from exception
        decision = PolicyDecision.ALLOW if result.succeeded else PolicyDecision.DENY
        await self._audit_events.append(
            AuditEventCreate(
                actor=actor_id,
                action="get_ticket_status",
                target=f"ticket:{ticket_number}",
                parameters_summary={"ticket_number": ticket_number},
                policy_decision=decision,
                execution_result=result.status.value,
                request_id=request_id,
            )
        )
        if not result.succeeded or result.observation is None:
            error_code = "tool_failed" if result.error is None else result.error.code
            raise ServiceDeskExecutionError(error_code)
        return result.observation

    async def cancel(
        self,
        *,
        confirmation_id: UUID,
        actor_id: str,
        actor_role: str,
        request_id: str,
    ) -> StoredPendingConfirmation:
        try:
            cancelled = await self._confirmations.cancel(
                confirmation_id,
                actor_id=actor_id,
                actor_role=actor_role,
                request_id=request_id,
            )
        except (ConfirmationAccessDeniedError, ConfirmationStateError):
            await self._audit_events.append(
                AuditEventCreate(
                    actor=actor_id,
                    action="cancel_action",
                    target=f"pending_confirmation:{confirmation_id}",
                    parameters_summary={},
                    policy_decision=PolicyDecision.DENY,
                    execution_result="not_cancelled",
                    request_id=request_id,
                )
            )
            raise
        return cancelled

    async def _propose_r1(
        self,
        *,
        actor_id: str,
        actor_role: str,
        request_id: str,
        action: str,
        arguments: dict[str, Any],
        parameters_summary: dict[str, Any],
        impact_summary: str,
        idempotency_key: str,
        source_agent_run_id: UUID | None,
        source_conversation_id: UUID | None,
    ) -> StoredPendingConfirmation:
        try:
            validation = self._gateway.validate_action(
                ToolExecutionRequest(
                    tool_name=action,
                    arguments=arguments,
                    context=ToolExecutionContext(
                        run_id=source_agent_run_id,
                        request_id=request_id,
                        node_name="prepare_action",
                        user_role=actor_role,
                        actor_id=actor_id,
                    ),
                )
            )
        except ToolActionValidationError:
            await self._audit_events.append(
                AuditEventCreate(
                    actor=actor_id,
                    action=action,
                    target=f"action:{action}",
                    parameters_summary=parameters_summary,
                    policy_decision=PolicyDecision.DENY,
                    execution_result="not_executed",
                    request_id=request_id,
                ),
            )
            raise
        if not validation.definition.has_side_effect:
            raise ToolActionValidationError(
                "confirmation_not_required",
                "R0 actions must execute automatically.",
            )
        return await self._confirmations.create(
            PendingConfirmationCreate(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                risk_level=ActionRisk.R1,
                status=ConfirmationStatus.PENDING,
                parameters=validation.arguments,
                parameters_summary=parameters_summary,
                impact_summary=impact_summary,
                idempotency_key=idempotency_key,
                request_fingerprint=_action_fingerprint(validation.arguments),
                source_agent_run_id=source_agent_run_id,
                source_conversation_id=source_conversation_id,
            ),
            request_id=request_id,
        )

    async def get_ticket(self, ticket_number: str) -> StoredTicket:
        """Internal read for API response materialization after authorization."""
        return await self._tickets.get_by_number(ticket_number)


def _fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _action_fingerprint(value: dict[str, Any]) -> str:
    """Exclude per-attempt trace IDs while binding the material business action."""
    material = {key: item for key, item in value.items() if key not in {"source_agent_run_id"}}
    return _fingerprint(material)
