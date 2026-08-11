"""PostgreSQL Adapter for tool execution audit records."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.tools.contracts import (
    ToolExecutionAudit,
    ToolExecutionStatus,
    ToolRiskLevel,
)
from enterprise_it_support.tools.models import ToolExecution


@dataclass(frozen=True)
class StoredToolExecution:
    id: UUID
    run_id: UUID | None
    actor_id: str | None
    pending_confirmation_id: UUID | None
    idempotency_key: str | None
    request_id: str
    node_name: str
    tool_name: str
    tool_version: str | None
    status: ToolExecutionStatus
    input_arguments: dict[str, object]
    observation: dict[str, object] | None
    risk_level: ToolRiskLevel | None
    has_side_effect: bool
    error_code: str | None
    error_message: str | None
    attempts: int
    latency_ms: int
    started_at: datetime
    completed_at: datetime


class ToolExecutionRepository:
    """Append and read tool audit rows without exposing SQL to Runtime."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, audit: ToolExecutionAudit) -> None:
        result = audit.result
        async with self._session_factory() as session, session.begin():
            existing = await session.get(ToolExecution, result.execution_id)
            if existing is not None:
                return
            session.add(
                ToolExecution(
                    id=result.execution_id,
                    run_id=audit.context.run_id,
                    actor_id=audit.context.actor_id,
                    pending_confirmation_id=audit.context.pending_confirmation_id,
                    idempotency_key=audit.context.idempotency_key,
                    request_id=audit.context.request_id,
                    node_name=audit.context.node_name,
                    tool_name=result.tool_name,
                    tool_version=result.tool_version,
                    status=result.status.value,
                    input_arguments=audit.arguments,
                    observation=result.observation,
                    required_risk_level=(
                        None if audit.risk_level is None else audit.risk_level.value
                    ),
                    has_side_effect=audit.has_side_effect,
                    error_code=None if result.error is None else result.error.code,
                    error_message=None if result.error is None else result.error.message,
                    attempts=result.attempts,
                    latency_ms=result.latency_ms,
                )
            )

    async def list_for_run(self, run_id: UUID) -> tuple[StoredToolExecution, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(ToolExecution)
                    .where(ToolExecution.run_id == run_id)
                    .order_by(ToolExecution.started_at, ToolExecution.id)
                )
            ).all()
            return tuple(self._stored(row) for row in rows)

    @staticmethod
    def _stored(row: ToolExecution) -> StoredToolExecution:
        return StoredToolExecution(
            id=row.id,
            run_id=row.run_id,
            actor_id=row.actor_id,
            pending_confirmation_id=row.pending_confirmation_id,
            idempotency_key=row.idempotency_key,
            request_id=row.request_id,
            node_name=row.node_name,
            tool_name=row.tool_name,
            tool_version=row.tool_version,
            status=ToolExecutionStatus(row.status),
            input_arguments=row.input_arguments,
            observation=row.observation,
            risk_level=(
                None if row.required_risk_level is None else ToolRiskLevel(row.required_risk_level)
            ),
            has_side_effect=row.has_side_effect,
            error_code=row.error_code,
            error_message=row.error_message,
            attempts=row.attempts,
            latency_ms=row.latency_ms,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
