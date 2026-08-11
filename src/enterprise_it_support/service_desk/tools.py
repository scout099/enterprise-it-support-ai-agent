"""Registered local service-desk tools and their PostgreSQL Adapter."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from enterprise_it_support.service_desk.domain import (
    AtomicToolAuditContext,
    TicketCreateCommand,
    TicketNotFoundError,
    TicketPriority,
)
from enterprise_it_support.service_desk.persistence import TicketRepository
from enterprise_it_support.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
    ToolRiskLevel,
)
from enterprise_it_support.tools.gateway import (
    ToolAuthorizationError,
    ToolRegistry,
    ToolResourceNotFoundError,
)


class StrictServiceDeskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreateTicketInput(StrictServiceDeskModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    priority: Annotated[TicketPriority, Field(strict=False)]
    requester_id: str = Field(min_length=1, max_length=128)
    assigned_to: str | None = Field(default=None, min_length=1, max_length=128)
    source_conversation_id: Annotated[UUID, Field(strict=False)] | None = None
    source_agent_run_id: Annotated[UUID, Field(strict=False)] | None = None
    diagnosis_summary: str = Field(min_length=1, max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CreateTicketOutput(StrictServiceDeskModel):
    ticket_id: Annotated[UUID, Field(strict=False)]
    ticket_number: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    priority: Annotated[TicketPriority, Field(strict=False)]
    status: str = Field(min_length=1, max_length=30)
    requester_id: str = Field(min_length=1, max_length=128)
    assigned_to: str | None
    source_conversation_id: Annotated[UUID, Field(strict=False)] | None
    source_agent_run_id: Annotated[UUID, Field(strict=False)] | None
    diagnosis_summary: str = Field(min_length=1, max_length=5000)
    created_at: str = Field(min_length=1, max_length=100)
    updated_at: str = Field(min_length=1, max_length=100)


class AddTicketCommentInput(StrictServiceDeskModel):
    ticket_number: str = Field(min_length=1, max_length=40)
    body: str = Field(min_length=1, max_length=5000)
    author_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)


class AddTicketCommentOutput(StrictServiceDeskModel):
    comment_id: Annotated[UUID, Field(strict=False)]
    ticket_number: str = Field(min_length=1, max_length=40)
    author_id: str = Field(min_length=1, max_length=128)
    created_at: str = Field(min_length=1, max_length=100)


class GetTicketStatusInput(StrictServiceDeskModel):
    ticket_number: str = Field(min_length=1, max_length=40)


class TicketCommentSummary(StrictServiceDeskModel):
    id: Annotated[UUID, Field(strict=False)]
    author_id: str = Field(min_length=1, max_length=128)
    body: str = Field(min_length=1, max_length=5000)
    created_at: str = Field(min_length=1, max_length=100)


class GetTicketStatusOutput(StrictServiceDeskModel):
    ticket_id: Annotated[UUID, Field(strict=False)]
    ticket_number: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    priority: Annotated[TicketPriority, Field(strict=False)]
    status: str = Field(min_length=1, max_length=30)
    requester_id: str = Field(min_length=1, max_length=128)
    assigned_to: str | None
    source_conversation_id: Annotated[UUID, Field(strict=False)] | None
    source_agent_run_id: Annotated[UUID, Field(strict=False)] | None
    diagnosis_summary: str = Field(min_length=1, max_length=5000)
    created_at: str = Field(min_length=1, max_length=100)
    updated_at: str = Field(min_length=1, max_length=100)
    comments: list[TicketCommentSummary] = Field(max_length=100)


class ServiceDeskToolAdapter:
    """Least-privileged local Adapter; no external service connections."""

    def __init__(self, tickets: TicketRepository) -> None:
        self._tickets = tickets

    async def create_ticket(
        self,
        value: CreateTicketInput,
        context: ToolExecutionContext,
    ) -> CreateTicketOutput:
        actor_id = _require_actor(context)
        tool_audit = _require_atomic_audit(context, actor_id)
        if actor_id != value.requester_id and context.user_role != "it_support":
            raise ToolAuthorizationError
        ticket = await self._tickets.create_ticket(
            TicketCreateCommand(
                title=value.title,
                description=value.description,
                category=value.category,
                priority=value.priority,
                requester_id=value.requester_id,
                assigned_to=value.assigned_to,
                source_conversation_id=value.source_conversation_id,
                source_agent_run_id=value.source_agent_run_id,
                diagnosis_summary=value.diagnosis_summary,
                idempotency_key=value.idempotency_key,
                request_id=context.request_id,
                tool_audit=tool_audit,
            )
        )
        return CreateTicketOutput.model_validate(ticket.as_tool_result())

    async def add_ticket_comment(
        self,
        value: AddTicketCommentInput,
        context: ToolExecutionContext,
    ) -> AddTicketCommentOutput:
        actor_id = _require_actor(context)
        tool_audit = _require_atomic_audit(context, actor_id)
        if actor_id != value.author_id and context.user_role != "it_support":
            raise ToolAuthorizationError
        try:
            ticket = await self._tickets.get_by_number(value.ticket_number)
        except TicketNotFoundError as exception:
            raise ToolResourceNotFoundError from exception
        if context.user_role != "it_support" and ticket.requester_id != actor_id:
            raise ToolAuthorizationError
        comment = await self._tickets.add_comment(
            ticket_number=value.ticket_number,
            author_id=value.author_id,
            body=value.body,
            idempotency_key=value.idempotency_key,
            request_id=context.request_id,
            tool_audit=tool_audit,
        )
        return AddTicketCommentOutput(
            comment_id=comment.id,
            ticket_number=value.ticket_number,
            author_id=comment.author_id,
            created_at=comment.created_at.isoformat(),
        )

    async def get_ticket_status(
        self,
        value: GetTicketStatusInput,
        context: ToolExecutionContext,
    ) -> GetTicketStatusOutput:
        actor_id = _require_actor(context)
        try:
            ticket = await self._tickets.get_by_number(value.ticket_number)
        except TicketNotFoundError as exception:
            raise ToolResourceNotFoundError from exception
        if context.user_role != "it_support" and ticket.requester_id != actor_id:
            raise ToolAuthorizationError
        comments = await self._tickets.list_comments(ticket.id)
        return GetTicketStatusOutput(
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            description=ticket.description,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status.value,
            requester_id=ticket.requester_id,
            assigned_to=ticket.assigned_to,
            source_conversation_id=ticket.source_conversation_id,
            source_agent_run_id=ticket.source_agent_run_id,
            diagnosis_summary=ticket.diagnosis_summary,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
            comments=[
                TicketCommentSummary(
                    id=comment.id,
                    author_id=comment.author_id,
                    body=comment.body,
                    created_at=comment.created_at.isoformat(),
                )
                for comment in comments
            ],
        )


def create_service_desk_tool_registry(
    adapter: ServiceDeskToolAdapter,
    registry: ToolRegistry | None = None,
) -> ToolRegistry:
    """Register the three Phase 8 local service-desk tools."""
    registry = registry or ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_ticket_status",
            version="1.0.0",
            description="Read one authorized local service-desk ticket.",
            input_schema=GetTicketStatusInput,
            output_schema=GetTicketStatusOutput,
            required_permissions=frozenset({"ticket:read"}),
            risk_level=ToolRiskLevel.R0,
            has_side_effect=False,
            timeout_seconds=2.0,
            retry_policy=RetryPolicy(max_attempts=1),
        ),
        adapter.get_ticket_status,
    )
    registry.register(
        ToolDefinition(
            name="create_ticket",
            version="1.0.0",
            description="Create one confirmed local service-desk ticket.",
            input_schema=CreateTicketInput,
            output_schema=CreateTicketOutput,
            required_permissions=frozenset({"ticket:create"}),
            risk_level=ToolRiskLevel.R1,
            has_side_effect=True,
            timeout_seconds=2.0,
            retry_policy=RetryPolicy(max_attempts=1),
        ),
        adapter.create_ticket,
    )
    registry.register(
        ToolDefinition(
            name="add_ticket_comment",
            version="1.0.0",
            description="Append one confirmed comment to an authorized local ticket.",
            input_schema=AddTicketCommentInput,
            output_schema=AddTicketCommentOutput,
            required_permissions=frozenset({"ticket:comment"}),
            risk_level=ToolRiskLevel.R1,
            has_side_effect=True,
            timeout_seconds=2.0,
            retry_policy=RetryPolicy(max_attempts=1),
        ),
        adapter.add_ticket_comment,
    )
    return registry


def service_desk_permissions() -> dict[str, frozenset[str]]:
    """Local demo permissions; resource ownership is enforced by the Adapter."""
    employee = frozenset({"ticket:read", "ticket:create", "ticket:comment"})
    support = employee | frozenset({"audit:read"})
    return {
        "employee": employee,
        "it_support": support,
        "project_maintainer": support,
    }


def _require_actor(context: ToolExecutionContext) -> str:
    actor_id = (context.actor_id or "").strip()
    if not actor_id:
        raise ToolAuthorizationError
    return actor_id


def _require_atomic_audit(
    context: ToolExecutionContext,
    actor_id: str,
) -> AtomicToolAuditContext:
    if (
        context.execution_id is None
        or context.pending_confirmation_id is None
        or context.idempotency_key is None
    ):
        raise ToolAuthorizationError
    return AtomicToolAuditContext(
        execution_id=context.execution_id,
        run_id=context.run_id,
        actor_id=actor_id,
        pending_confirmation_id=context.pending_confirmation_id,
        idempotency_key=context.idempotency_key,
        request_id=context.request_id,
        node_name=context.node_name,
    )
