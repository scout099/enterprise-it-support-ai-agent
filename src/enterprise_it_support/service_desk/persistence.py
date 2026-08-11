"""Transactional PostgreSQL repositories for tickets, confirmations, and audit."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.service_desk.domain import (
    ActionRisk,
    AtomicToolAuditContext,
    AuditEventCreate,
    ConfirmationAccessDeniedError,
    ConfirmationNotFoundError,
    ConfirmationStateError,
    ConfirmationStatus,
    IdempotencyConflictError,
    PendingConfirmationCreate,
    PolicyDecision,
    StoredAuditEvent,
    StoredPendingConfirmation,
    StoredTicket,
    StoredTicketComment,
    TicketCreateCommand,
    TicketNotFoundError,
    TicketPriority,
    TicketStatus,
)
from enterprise_it_support.service_desk.models import (
    AuditEvent,
    PendingConfirmation,
    Ticket,
    TicketComment,
)
from enterprise_it_support.tools.contracts import ToolDefinition, ToolExecutionRequest
from enterprise_it_support.tools.models import ToolExecution


class TicketRepository:
    """Own ticket and comment SQL, including final idempotency protection."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_ticket(self, command: TicketCreateCommand) -> StoredTicket:
        async with self._session_factory() as session, session.begin():
            await _idempotency_lock(session, f"ticket:{command.idempotency_key}")
            existing = await session.scalar(
                select(Ticket).where(Ticket.idempotency_key == command.idempotency_key)
            )
            if existing is not None:
                self._ensure_same_ticket(existing, command)
                return self._stored_ticket(existing)
            sequence = int(await session.scalar(text("SELECT nextval('ticket_number_seq')")) or 0)
            number = f"IT-{datetime.now(UTC):%Y%m%d}-{sequence:06d}"
            row = Ticket(
                ticket_number=number,
                title=command.title,
                description=command.description,
                category=command.category,
                priority=command.priority.value,
                status=TicketStatus.OPEN.value,
                requester_id=command.requester_id,
                assigned_to=command.assigned_to,
                source_conversation_id=command.source_conversation_id,
                source_agent_run_id=command.source_agent_run_id,
                diagnosis_summary=command.diagnosis_summary,
                idempotency_key=command.idempotency_key,
            )
            session.add(row)
            await session.flush()
            session.add(
                AuditEvent(
                    actor=command.requester_id,
                    action="create_ticket",
                    target=f"ticket:{row.ticket_number}",
                    parameters_summary={
                        "title_length": len(command.title),
                        "description_length": len(command.description),
                        "category": command.category,
                        "priority": command.priority.value,
                        "requester_id": command.requester_id,
                        "diagnosis_summary_length": len(command.diagnosis_summary),
                    },
                    policy_decision=PolicyDecision.ALLOW.value,
                    execution_result="succeeded",
                    request_id=command.request_id,
                )
            )
            session.add(
                _successful_tool_execution(
                    audit=command.tool_audit,
                    tool_name="create_ticket",
                    input_arguments={
                        "title": {
                            "redacted": "[TEXT REDACTED]",
                            "length": len(command.title),
                        },
                        "description": {
                            "redacted": "[TEXT REDACTED]",
                            "length": len(command.description),
                        },
                        "category": command.category,
                        "priority": command.priority.value,
                        "requester_id": command.requester_id,
                        "diagnosis_summary": {
                            "redacted": "[TEXT REDACTED]",
                            "length": len(command.diagnosis_summary),
                        },
                        "idempotency_key": command.idempotency_key,
                    },
                    observation={
                        "ticket_number": row.ticket_number,
                        "status": row.status,
                    },
                )
            )
            await session.refresh(row)
            return self._stored_ticket(row)

    async def add_comment(
        self,
        *,
        ticket_number: str,
        author_id: str,
        body: str,
        idempotency_key: str,
        request_id: str,
        tool_audit: AtomicToolAuditContext,
    ) -> StoredTicketComment:
        async with self._session_factory() as session, session.begin():
            await _idempotency_lock(session, f"comment:{idempotency_key}")
            existing = await session.scalar(
                select(TicketComment).where(TicketComment.idempotency_key == idempotency_key)
            )
            if existing is not None:
                ticket = await session.get(Ticket, existing.ticket_id)
                if (
                    ticket is None
                    or ticket.ticket_number != ticket_number
                    or existing.author_id != author_id
                    or existing.body != body
                ):
                    raise IdempotencyConflictError(
                        "Comment idempotency key was reused with different parameters"
                    )
                return self._stored_comment(existing)
            ticket = await session.scalar(
                select(Ticket).where(Ticket.ticket_number == ticket_number).with_for_update()
            )
            if ticket is None:
                raise TicketNotFoundError(ticket_number)
            row = TicketComment(
                ticket_id=ticket.id,
                author_id=author_id,
                body=body,
                idempotency_key=idempotency_key,
            )
            session.add(row)
            session.add(
                AuditEvent(
                    actor=author_id,
                    action="add_ticket_comment",
                    target=f"ticket:{ticket_number}",
                    parameters_summary={
                        "ticket_number": ticket_number,
                        "comment_length": len(body),
                        "author_id": author_id,
                    },
                    policy_decision=PolicyDecision.ALLOW.value,
                    execution_result="succeeded",
                    request_id=request_id,
                )
            )
            session.add(
                _successful_tool_execution(
                    audit=tool_audit,
                    tool_name="add_ticket_comment",
                    input_arguments={
                        "ticket_number": ticket_number,
                        "body": {
                            "redacted": "[TEXT REDACTED]",
                            "length": len(body),
                        },
                        "author_id": author_id,
                        "idempotency_key": idempotency_key,
                    },
                    observation={
                        "ticket_number": ticket_number,
                        "comment_id": str(row.id),
                    },
                )
            )
            ticket.updated_at = datetime.now(UTC)
            await session.flush()
            await session.refresh(row)
            return self._stored_comment(row)

    async def get_by_number(self, ticket_number: str) -> StoredTicket:
        async with self._session_factory() as session:
            row = await session.scalar(select(Ticket).where(Ticket.ticket_number == ticket_number))
            if row is None:
                raise TicketNotFoundError(ticket_number)
            return self._stored_ticket(row)

    async def list_comments(
        self,
        ticket_id: UUID,
    ) -> tuple[StoredTicketComment, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(TicketComment)
                    .where(TicketComment.ticket_id == ticket_id)
                    .order_by(TicketComment.created_at, TicketComment.id)
                )
            ).all()
            return tuple(self._stored_comment(row) for row in rows)

    @staticmethod
    def _ensure_same_ticket(row: Ticket, command: TicketCreateCommand) -> None:
        values = (
            row.title,
            row.description,
            row.category,
            row.priority,
            row.requester_id,
            row.source_conversation_id,
            row.source_agent_run_id,
            row.diagnosis_summary,
        )
        expected = (
            command.title,
            command.description,
            command.category,
            command.priority.value,
            command.requester_id,
            command.source_conversation_id,
            command.source_agent_run_id,
            command.diagnosis_summary,
        )
        if values != expected:
            raise IdempotencyConflictError(
                "Ticket idempotency key was reused with different parameters"
            )

    @staticmethod
    def _stored_ticket(row: Ticket) -> StoredTicket:
        return StoredTicket(
            id=row.id,
            ticket_number=row.ticket_number,
            title=row.title,
            description=row.description,
            category=row.category,
            priority=TicketPriority(row.priority),
            status=TicketStatus(row.status),
            requester_id=row.requester_id,
            assigned_to=row.assigned_to,
            source_conversation_id=row.source_conversation_id,
            source_agent_run_id=row.source_agent_run_id,
            diagnosis_summary=row.diagnosis_summary,
            idempotency_key=row.idempotency_key,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _stored_comment(row: TicketComment) -> StoredTicketComment:
        return StoredTicketComment(
            id=row.id,
            ticket_id=row.ticket_id,
            author_id=row.author_id,
            body=row.body,
            idempotency_key=row.idempotency_key,
            created_at=row.created_at,
        )


class PendingConfirmationRepository:
    """Persist, claim, and revalidate R1/R3 action requests."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        command: PendingConfirmationCreate,
        *,
        request_id: str,
    ) -> StoredPendingConfirmation:
        async with self._session_factory() as session, session.begin():
            await _idempotency_lock(
                session,
                f"confirmation:{command.action}:{command.idempotency_key}",
            )
            existing = await session.scalar(
                select(PendingConfirmation).where(
                    PendingConfirmation.action == command.action,
                    PendingConfirmation.idempotency_key == command.idempotency_key,
                )
            )
            if existing is not None:
                if (
                    existing.request_fingerprint != command.request_fingerprint
                    or existing.actor_id != command.actor_id
                    or existing.actor_role != command.actor_role
                    or existing.risk_level != command.risk_level.value
                ):
                    raise IdempotencyConflictError(
                        "Confirmation idempotency key was reused with different parameters"
                    )
                row = existing
            else:
                row = PendingConfirmation(
                    actor_id=command.actor_id,
                    actor_role=command.actor_role,
                    action=command.action,
                    risk_level=command.risk_level.value,
                    status=command.status.value,
                    parameters=command.parameters,
                    parameters_summary=command.parameters_summary,
                    impact_summary=command.impact_summary,
                    idempotency_key=command.idempotency_key,
                    request_fingerprint=command.request_fingerprint,
                    source_agent_run_id=command.source_agent_run_id,
                    source_conversation_id=command.source_conversation_id,
                )
                session.add(row)
                await session.flush()
            session.add(
                AuditEvent(
                    actor=command.actor_id,
                    action=command.action,
                    target=f"pending_confirmation:{row.id}",
                    parameters_summary=row.parameters_summary,
                    policy_decision=(
                        PolicyDecision.CONFIRMATION_REQUIRED.value
                        if command.risk_level is ActionRisk.R1
                        else PolicyDecision.APPROVAL_REQUIRED.value
                    ),
                    execution_result="not_executed",
                    request_id=request_id,
                )
            )
            await session.flush()
            await session.refresh(row)
            return self._stored(row)

    async def claim(
        self,
        confirmation_id: UUID,
        *,
        actor_id: str,
        actor_role: str,
    ) -> StoredPendingConfirmation:
        async with self._session_factory() as session, session.begin():
            row = await session.get(
                PendingConfirmation,
                confirmation_id,
                with_for_update=True,
            )
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            self._authorize(row, actor_id=actor_id, actor_role=actor_role)
            if row.status == ConfirmationStatus.EXECUTED.value:
                return self._stored(row)
            if row.status == ConfirmationStatus.APPROVAL_REQUIRED.value:
                raise ConfirmationStateError("R3 approval requests cannot be executed")
            if row.status != ConfirmationStatus.PENDING.value:
                raise ConfirmationStateError(
                    f"Confirmation cannot execute from status {row.status}"
                )
            row.status = ConfirmationStatus.EXECUTING.value
            row.confirmed_at = datetime.now(UTC)
            await session.flush()
            return self._stored(row)

    async def validate_for_execution(
        self,
        request: ToolExecutionRequest,
        definition: ToolDefinition,
    ) -> None:
        confirmation_id = request.context.pending_confirmation_id
        if confirmation_id is None:
            raise ConfirmationStateError("Missing confirmation ID")
        async with self._session_factory() as session:
            row = await session.get(PendingConfirmation, confirmation_id)
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            if (
                row.status != ConfirmationStatus.EXECUTING.value
                or row.risk_level != ActionRisk.R1.value
                or row.action != definition.name
                or row.actor_id != request.context.actor_id
                or row.actor_role != request.context.user_role
                or row.idempotency_key != request.context.idempotency_key
                or row.parameters != request.arguments
            ):
                raise ConfirmationStateError("Confirmation evidence does not match action")

    async def complete(
        self,
        confirmation_id: UUID,
        result: dict[str, Any],
    ) -> StoredPendingConfirmation:
        async with self._session_factory() as session, session.begin():
            row = await session.get(
                PendingConfirmation,
                confirmation_id,
                with_for_update=True,
            )
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            row.status = ConfirmationStatus.EXECUTED.value
            row.result = result
            row.error_code = None
            row.executed_at = datetime.now(UTC)
            await session.flush()
            return self._stored(row)

    async def fail(
        self,
        confirmation_id: UUID,
        error_code: str,
    ) -> StoredPendingConfirmation:
        async with self._session_factory() as session, session.begin():
            row = await session.get(
                PendingConfirmation,
                confirmation_id,
                with_for_update=True,
            )
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            row.status = ConfirmationStatus.FAILED.value
            row.error_code = error_code
            row.executed_at = datetime.now(UTC)
            await session.flush()
            return self._stored(row)

    async def cancel(
        self,
        confirmation_id: UUID,
        *,
        actor_id: str,
        actor_role: str,
        request_id: str,
    ) -> StoredPendingConfirmation:
        async with self._session_factory() as session, session.begin():
            row = await session.get(
                PendingConfirmation,
                confirmation_id,
                with_for_update=True,
            )
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            self._authorize(row, actor_id=actor_id, actor_role=actor_role)
            if row.status == ConfirmationStatus.CANCELLED.value:
                return self._stored(row)
            if row.status != ConfirmationStatus.PENDING.value:
                raise ConfirmationStateError(
                    f"Confirmation cannot be cancelled from status {row.status}"
                )
            row.status = ConfirmationStatus.CANCELLED.value
            row.cancelled_at = datetime.now(UTC)
            await session.flush()
            session.add(
                AuditEvent(
                    actor=actor_id,
                    action="cancel_action",
                    target=f"pending_confirmation:{confirmation_id}",
                    parameters_summary={"action": row.action},
                    policy_decision=PolicyDecision.ALLOW.value,
                    execution_result="cancelled",
                    request_id=request_id,
                )
            )
            await session.flush()
            return self._stored(row)

    async def get(self, confirmation_id: UUID) -> StoredPendingConfirmation:
        async with self._session_factory() as session:
            row = await session.get(PendingConfirmation, confirmation_id)
            if row is None:
                raise ConfirmationNotFoundError(str(confirmation_id))
            return self._stored(row)

    @staticmethod
    def _authorize(
        row: PendingConfirmation,
        *,
        actor_id: str,
        actor_role: str,
    ) -> None:
        if row.actor_id != actor_id or row.actor_role != actor_role:
            raise ConfirmationAccessDeniedError("Confirmation does not belong to caller")

    @staticmethod
    def _stored(row: PendingConfirmation) -> StoredPendingConfirmation:
        return StoredPendingConfirmation(
            id=row.id,
            actor_id=row.actor_id,
            actor_role=row.actor_role,
            action=row.action,
            risk_level=ActionRisk(row.risk_level),
            status=ConfirmationStatus(row.status),
            parameters=row.parameters,
            parameters_summary=row.parameters_summary,
            impact_summary=row.impact_summary,
            idempotency_key=row.idempotency_key,
            request_fingerprint=row.request_fingerprint,
            source_agent_run_id=row.source_agent_run_id,
            source_conversation_id=row.source_conversation_id,
            result=row.result,
            error_code=row.error_code,
            created_at=row.created_at,
            confirmed_at=row.confirmed_at,
            executed_at=row.executed_at,
            cancelled_at=row.cancelled_at,
        )


class AuditEventRepository:
    """Append and page sanitized audit events."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def append(self, command: AuditEventCreate) -> StoredAuditEvent:
        async with self._session_factory() as session, session.begin():
            row = AuditEvent(
                actor=command.actor,
                action=command.action,
                target=command.target,
                parameters_summary=command.parameters_summary,
                policy_decision=command.policy_decision.value,
                execution_result=command.execution_result,
                request_id=command.request_id,
            )
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return self._stored(row)

    async def list_recent(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[StoredAuditEvent, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(AuditEvent)
                    .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
            return tuple(self._stored(row) for row in rows)

    @staticmethod
    def _stored(row: AuditEvent) -> StoredAuditEvent:
        return StoredAuditEvent(
            id=row.id,
            actor=row.actor,
            action=row.action,
            target=row.target,
            parameters_summary=row.parameters_summary,
            policy_decision=PolicyDecision(row.policy_decision),
            execution_result=row.execution_result,
            request_id=row.request_id,
            created_at=row.created_at,
        )


async def _idempotency_lock(session: AsyncSession, key: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": key},
    )


def _successful_tool_execution(
    *,
    audit: AtomicToolAuditContext,
    tool_name: str,
    input_arguments: dict[str, Any],
    observation: dict[str, Any],
) -> ToolExecution:
    return ToolExecution(
        id=audit.execution_id,
        run_id=audit.run_id,
        actor_id=audit.actor_id,
        pending_confirmation_id=audit.pending_confirmation_id,
        idempotency_key=audit.idempotency_key,
        request_id=audit.request_id,
        node_name=audit.node_name,
        tool_name=tool_name,
        tool_version="1.0.0",
        status="succeeded",
        input_arguments=input_arguments,
        observation=observation,
        required_risk_level="r1",
        has_side_effect=True,
        error_code=None,
        error_message=None,
        attempts=1,
        latency_ms=0,
    )
