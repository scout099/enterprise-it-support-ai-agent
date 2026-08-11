"""Confirmed, idempotent local ticket behavior through public service seams."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.agent_runtime.models import AgentRun
from enterprise_it_support.agent_runtime.persistence import AgentRunRepository
from enterprise_it_support.agent_runtime.state import initial_agent_state
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager
from enterprise_it_support.service_desk.domain import (
    ConfirmationStateError,
    ConfirmationStatus,
    IdempotencyConflictError,
)
from enterprise_it_support.service_desk.models import (
    AuditEvent,
    PendingConfirmation,
    Ticket,
    TicketComment,
)
from enterprise_it_support.service_desk.persistence import (
    AuditEventRepository,
    PendingConfirmationRepository,
    TicketRepository,
)
from enterprise_it_support.service_desk.service import (
    ServiceDeskExecutionError,
    ServiceDeskService,
)
from enterprise_it_support.service_desk.tools import (
    ServiceDeskToolAdapter,
    create_service_desk_tool_registry,
    service_desk_permissions,
)
from enterprise_it_support.tools.contracts import (
    ToolExecutionContext,
    ToolExecutionRequest,
)
from enterprise_it_support.tools.gateway import (
    RolePermissionPolicy,
    ToolActionValidationError,
    ToolExecutionGateway,
)
from enterprise_it_support.tools.models import ToolExecution
from enterprise_it_support.tools.persistence import ToolExecutionRepository


@pytest.fixture
async def service_desk_database(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DatabaseManager, ServiceDeskService]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory() as session, session.begin():
        await session.execute(delete(AuditEvent))
        await session.execute(delete(ToolExecution))
        await session.execute(delete(PendingConfirmation))
        await session.execute(delete(TicketComment))
        await session.execute(delete(Ticket))
        await session.execute(delete(AgentRun))

    ticket_repository = TicketRepository(database.session_factory)
    confirmation_repository = PendingConfirmationRepository(database.session_factory)
    audit_repository = AuditEventRepository(database.session_factory)
    tool_repository = ToolExecutionRepository(database.session_factory)
    gateway = ToolExecutionGateway(
        registry=create_service_desk_tool_registry(ServiceDeskToolAdapter(ticket_repository)),
        policy=RolePermissionPolicy(service_desk_permissions()),
        execution_store=tool_repository,
        confirmation_validator=confirmation_repository,
    )
    service = ServiceDeskService(
        gateway=gateway,
        confirmations=confirmation_repository,
        tickets=ticket_repository,
        audit_events=audit_repository,
    )
    try:
        yield database, service
    finally:
        await database.close()
        get_settings.cache_clear()


@pytest.mark.integration
async def test_ticket_is_not_created_until_confirmed_and_confirmation_is_idempotent(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, service = service_desk_database
    run_id = uuid4()
    state = initial_agent_state(
        run_id=str(run_id),
        request_id="phase8-confirm",
        conversation_id=None,
        user_message="Create a ticket because VPN diagnosis failed",
        user_role="employee",
    )
    await AgentRunRepository(database.session_factory).create_run(state)

    pending = await service.propose_create_ticket(
        actor_id="employee-001",
        actor_role="employee",
        request_id="phase8-confirm",
        idempotency_key="create-ticket-once",
        title="VPN connection still failing",
        description="VPN diagnosis could not resolve the issue.",
        category="vpn",
        priority="medium",
        source_conversation_id=None,
        source_agent_run_id=run_id,
        diagnosis_summary="Network healthy; mock VPN checks did not resolve the issue.",
    )
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 0

    first = await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-001",
        actor_role="employee",
        request_id="phase8-confirmed",
    )
    second = await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-001",
        actor_role="employee",
        request_id="phase8-confirm-replay",
    )

    assert first.result == second.result
    assert first.result is not None
    assert first.result["ticket_number"].startswith("IT-")
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 1
        assert await session.scalar(select(func.count()).select_from(ToolExecution)) == 1


@pytest.mark.integration
async def test_reused_idempotency_key_conflicts_and_audit_redacts_sensitive_text(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, service = service_desk_database
    fictional_secret = "Bearer fictional-phase8-token"
    pending = await service.propose_create_ticket(
        actor_id="employee-002",
        actor_role="employee",
        request_id="phase8-redaction",
        idempotency_key="redacted-ticket-key",
        title=f"Outlook issue {fictional_secret}",
        description=f"Mail failed. {fictional_secret}",
        category="outlook",
        priority="low",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary=f"Diagnosis stopped. {fictional_secret}",
    )
    replay = await service.propose_create_ticket(
        actor_id="employee-002",
        actor_role="employee",
        request_id="phase8-redaction-replay",
        idempotency_key="redacted-ticket-key",
        title=f"Outlook issue {fictional_secret}",
        description=f"Mail failed. {fictional_secret}",
        category="outlook",
        priority="low",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary=f"Diagnosis stopped. {fictional_secret}",
    )
    assert replay.id == pending.id
    with pytest.raises(IdempotencyConflictError):
        await service.propose_create_ticket(
            actor_id="employee-002",
            actor_role="employee",
            request_id="phase8-redaction-conflict",
            idempotency_key="redacted-ticket-key",
            title="Different issue",
            description="Different description",
            category="account",
            priority="high",
            source_conversation_id=None,
            source_agent_run_id=None,
            diagnosis_summary="Different diagnosis",
        )

    await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-002",
        actor_role="employee",
        request_id="phase8-redaction-confirm",
    )
    async with database.session_factory() as session:
        audit_payloads = (await session.scalars(select(AuditEvent.parameters_summary))).all()
        tool_payloads = (await session.scalars(select(ToolExecution.input_arguments))).all()
    persisted_audit = repr([*audit_payloads, *tool_payloads])
    assert fictional_secret not in persisted_audit
    assert "fictional-phase8-token" not in persisted_audit
    assert "description_length" in persisted_audit
    assert "[TEXT REDACTED]" in persisted_audit
    async with database.session_factory() as session:
        events = (await session.scalars(select(AuditEvent))).all()
        execution = await session.scalar(select(ToolExecution))
    assert execution is not None
    assert execution.actor_id == "employee-002"
    assert execution.pending_confirmation_id == pending.id
    assert execution.idempotency_key == "redacted-ticket-key"
    assert execution.has_side_effect is True
    assert execution.required_risk_level == "r1"
    assert all(event.actor for event in events)
    assert all(event.action for event in events)
    assert all(event.target for event in events)
    assert all(event.policy_decision for event in events)
    assert all(event.execution_result for event in events)
    assert all(event.request_id for event in events)
    assert all(event.created_at for event in events)


@pytest.mark.integration
async def test_comment_requires_confirmation_and_r0_status_enforces_ticket_ownership(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, service = service_desk_database
    pending = await service.propose_create_ticket(
        actor_id="employee-003",
        actor_role="employee",
        request_id="phase8-status",
        idempotency_key="status-ticket-key",
        title="Account issue",
        description="Account remains locked.",
        category="account",
        priority="medium",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary="Read-only diagnosis found the account locked.",
    )
    created = await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-003",
        actor_role="employee",
        request_id="phase8-status-confirm",
    )
    assert created.result is not None
    ticket_number = str(created.result["ticket_number"])

    comment = await service.propose_add_comment(
        actor_id="employee-003",
        actor_role="employee",
        request_id="phase8-comment",
        idempotency_key="comment-ticket-key",
        ticket_number=ticket_number,
        body="The issue is still reproducible.",
    )
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(TicketComment)) == 0
    await service.confirm(
        confirmation_id=comment.id,
        actor_id="employee-003",
        actor_role="employee",
        request_id="phase8-comment-confirm",
    )
    status = await service.get_ticket_status(
        ticket_number=ticket_number,
        actor_id="employee-003",
        actor_role="employee",
        request_id="phase8-status-read",
    )
    assert status["status"] == "open"
    assert len(status["comments"]) == 1
    with pytest.raises(ServiceDeskExecutionError):
        await service.get_ticket_status(
            ticket_number=ticket_number,
            actor_id="employee-other",
            actor_role="employee",
            request_id="phase8-status-denied",
        )


@pytest.mark.integration
async def test_guest_cannot_prepare_r1_and_r3_is_approval_only(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    _, service = service_desk_database
    with pytest.raises(ToolActionValidationError) as denied:
        await service.propose_create_ticket(
            actor_id="guest-001",
            actor_role="guest",
            request_id="phase8-guest",
            idempotency_key="guest-ticket-key",
            title="Denied",
            description="Guest should not create tickets.",
            category="other",
            priority="low",
            source_conversation_id=None,
            source_agent_run_id=None,
            diagnosis_summary="No authorized diagnosis.",
        )
    assert denied.value.code == "tool_permission_denied"

    approval = await service.create_approval_request(
        actor_id="employee-004",
        actor_role="employee",
        request_id="phase8-r3",
        idempotency_key="password-reset-approval",
        action="reset_password",
        target="current_account",
        source_agent_run_id=None,
    )
    assert approval.status is ConfirmationStatus.APPROVAL_REQUIRED
    with pytest.raises(ConfirmationStateError):
        await service.confirm(
            confirmation_id=approval.id,
            actor_id="employee-004",
            actor_role="employee",
            request_id="phase8-r3-confirm",
        )
    with pytest.raises(IdempotencyConflictError):
        await service.create_approval_request(
            actor_id="employee-other",
            actor_role="employee",
            request_id="phase8-r3-cross-actor",
            idempotency_key="password-reset-approval",
            action="reset_password",
            target="current_account",
            source_agent_run_id=None,
        )


@pytest.mark.integration
async def test_gateway_cannot_execute_r1_without_persisted_confirmation(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, _ = service_desk_database
    tickets = TicketRepository(database.session_factory)
    gateway = ToolExecutionGateway(
        registry=create_service_desk_tool_registry(ServiceDeskToolAdapter(tickets)),
        policy=RolePermissionPolicy(service_desk_permissions()),
        execution_store=ToolExecutionRepository(database.session_factory),
        confirmation_validator=PendingConfirmationRepository(database.session_factory),
    )

    result = await gateway.execute(
        ToolExecutionRequest(
            tool_name="create_ticket",
            arguments={
                "title": "Bypass attempt",
                "description": "Calling the Gateway without confirmation must fail.",
                "category": "other",
                "priority": "medium",
                "requester_id": "employee-bypass",
                "assigned_to": None,
                "source_conversation_id": None,
                "source_agent_run_id": None,
                "diagnosis_summary": "No confirmed action exists.",
                "idempotency_key": "gateway-bypass-ticket",
            },
            context=ToolExecutionContext(
                run_id=None,
                request_id="phase8-gateway-bypass",
                node_name="direct_gateway_attempt",
                user_role="employee",
                actor_id="employee-bypass",
            ),
        )
    )

    assert result.succeeded is False
    assert result.error is not None
    assert result.error.code == "confirmation_required"
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 0


@pytest.mark.integration
async def test_pending_confirmation_rolls_back_when_proposal_audit_cannot_persist(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, service = service_desk_database

    with pytest.raises(SQLAlchemyError):
        await service.propose_create_ticket(
            actor_id="employee-atomic-proposal",
            actor_role="employee",
            request_id="x" * 129,
            idempotency_key="atomic-proposal-ticket",
            title="Atomic proposal",
            description="The pending row must roll back with its audit event.",
            category="other",
            priority="medium",
            source_conversation_id=None,
            source_agent_run_id=None,
            diagnosis_summary="Inject an audit constraint failure.",
        )

    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PendingConfirmation)) == 0
        assert await session.scalar(select(func.count()).select_from(AuditEvent)) == 0


@pytest.mark.integration
async def test_confirmed_tool_failure_creates_no_ticket_and_is_fully_audited(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, _ = service_desk_database
    tickets = TicketRepository(database.session_factory)
    confirmations = PendingConfirmationRepository(database.session_factory)
    audit_events = AuditEventRepository(database.session_factory)

    class FailingAdapter(ServiceDeskToolAdapter):
        async def create_ticket(self, value, context):
            _ = value, context
            raise RuntimeError("fictional-tool-secret")

    gateway = ToolExecutionGateway(
        registry=create_service_desk_tool_registry(FailingAdapter(tickets)),
        policy=RolePermissionPolicy(service_desk_permissions()),
        execution_store=ToolExecutionRepository(database.session_factory),
        confirmation_validator=confirmations,
    )
    service = ServiceDeskService(
        gateway=gateway,
        confirmations=confirmations,
        tickets=tickets,
        audit_events=audit_events,
    )
    pending = await service.propose_create_ticket(
        actor_id="employee-005",
        actor_role="employee",
        request_id="phase8-tool-failure",
        idempotency_key="failed-tool-ticket",
        title="Tool failure test",
        description="This write must fail safely.",
        category="other",
        priority="medium",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary="The injected Adapter fails before ticket persistence.",
    )
    failed = await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-005",
        actor_role="employee",
        request_id="phase8-tool-failure-confirm",
    )

    assert failed.status is ConfirmationStatus.FAILED
    assert failed.error_code == "tool_execution_failed"
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 0
        execution = await session.scalar(select(ToolExecution))
        events = (await session.scalars(select(AuditEvent))).all()
    assert execution is not None
    assert execution.status == "failed"
    assert execution.error_code == "tool_execution_failed"
    assert "fictional-tool-secret" not in repr(execution)
    assert [event.execution_result for event in events] == [
        "not_executed",
        "failed:tool_execution_failed",
    ]


@pytest.mark.integration
async def test_successful_write_keeps_atomic_audit_when_gateway_store_fails(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, _ = service_desk_database
    tickets = TicketRepository(database.session_factory)
    confirmations = PendingConfirmationRepository(database.session_factory)
    audit_events = AuditEventRepository(database.session_factory)

    class FailingExecutionStore:
        async def record(self, _audit) -> None:
            raise RuntimeError("fictional-audit-store-secret")

    gateway = ToolExecutionGateway(
        registry=create_service_desk_tool_registry(ServiceDeskToolAdapter(tickets)),
        policy=RolePermissionPolicy(service_desk_permissions()),
        execution_store=FailingExecutionStore(),
        confirmation_validator=confirmations,
    )
    service = ServiceDeskService(
        gateway=gateway,
        confirmations=confirmations,
        tickets=tickets,
        audit_events=audit_events,
    )
    pending = await service.propose_create_ticket(
        actor_id="employee-006",
        actor_role="employee",
        request_id="phase8-atomic-audit",
        idempotency_key="atomic-audit-ticket",
        title="Atomic audit test",
        description="The gateway audit Adapter fails after the local transaction.",
        category="other",
        priority="medium",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary="The ticket and its two local audit facts must commit together.",
    )
    completed = await service.confirm(
        confirmation_id=pending.id,
        actor_id="employee-006",
        actor_role="employee",
        request_id="phase8-atomic-audit-confirm",
    )

    assert completed.status is ConfirmationStatus.EXECUTED
    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 1
        assert await session.scalar(select(func.count()).select_from(ToolExecution)) == 1
        events = (await session.scalars(select(AuditEvent))).all()
    assert [event.execution_result for event in events] == ["not_executed", "succeeded"]
    assert "fictional-audit-store-secret" not in repr(events)


@pytest.mark.integration
async def test_r0_audit_store_failure_returns_stable_service_error(
    service_desk_database: tuple[DatabaseManager, ServiceDeskService],
) -> None:
    database, service = service_desk_database
    proposed = await service.propose_create_ticket(
        actor_id="employee-r0-audit",
        actor_role="employee",
        request_id="phase8-r0-audit-create",
        idempotency_key="r0-audit-ticket",
        title="R0 audit failure",
        description="Create a ticket before injecting the read audit failure.",
        category="other",
        priority="low",
        source_conversation_id=None,
        source_agent_run_id=None,
        diagnosis_summary="Ticket creation succeeds before the read failure.",
    )
    created = await service.confirm(
        confirmation_id=proposed.id,
        actor_id="employee-r0-audit",
        actor_role="employee",
        request_id="phase8-r0-audit-confirm",
    )
    assert created.result is not None

    class FailingExecutionStore:
        async def record(self, _audit) -> None:
            raise RuntimeError("fictional-r0-audit-secret")

    tickets = TicketRepository(database.session_factory)
    failing_service = ServiceDeskService(
        gateway=ToolExecutionGateway(
            registry=create_service_desk_tool_registry(ServiceDeskToolAdapter(tickets)),
            policy=RolePermissionPolicy(service_desk_permissions()),
            execution_store=FailingExecutionStore(),
            confirmation_validator=PendingConfirmationRepository(database.session_factory),
        ),
        confirmations=PendingConfirmationRepository(database.session_factory),
        tickets=tickets,
        audit_events=AuditEventRepository(database.session_factory),
    )

    with pytest.raises(ServiceDeskExecutionError) as failed:
        await failing_service.get_ticket_status(
            ticket_number=str(created.result["ticket_number"]),
            actor_id="employee-r0-audit",
            actor_role="employee",
            request_id="phase8-r0-audit-read",
        )
    assert failed.value.code == "tool_audit_unavailable"
