"""Transactional Agent Run and Step persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.agent_runtime.models import AgentRun, AgentStep
from enterprise_it_support.agent_runtime.state import (
    AgentRunStatus,
    AgentState,
    AgentStepStatus,
)


class AgentRunNotFoundError(LookupError):
    """Raised when a requested Agent Run does not exist."""


@dataclass(frozen=True)
class StoredAgentStep:
    id: UUID
    sequence_number: int
    node_name: str
    status: AgentStepStatus
    state_snapshot: dict[str, Any]
    error_code: str | None
    error_message: str | None
    latency_ms: int
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class StoredAgentRun:
    id: UUID
    request_id: str
    conversation_id: UUID | None
    status: AgentRunStatus
    intent: str | None
    intent_confidence: float
    risk_level: str
    current_node: str | None
    state: AgentState
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None
    steps: tuple[StoredAgentStep, ...]


class AgentRunStore(Protocol):
    """Persistence behavior required by AgentRuntime."""

    async def create_run(self, state: AgentState) -> None: ...

    async def save_step(
        self,
        *,
        state: AgentState,
        node_name: str,
        status: AgentStepStatus,
        latency_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...

    async def update_run(self, state: AgentState) -> None: ...

    async def get(self, run_id: UUID) -> StoredAgentRun: ...


class AgentRunRepository:
    """Persist latest state and append-only node attempts in PostgreSQL."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_run(self, state: AgentState) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                AgentRun(
                    id=UUID(state["run_id"]),
                    request_id=state["request_id"],
                    conversation_id=_optional_uuid(state["conversation_id"]),
                    status=state["status"],
                    intent=state["intent"],
                    intent_confidence=state["intent_confidence"],
                    risk_level=state["risk_level"],
                    current_node=state["current_node"],
                    state=dict(state),
                )
            )

    async def save_step(
        self,
        *,
        state: AgentState,
        node_name: str,
        status: AgentStepStatus,
        latency_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            run = await session.scalar(
                select(AgentRun).where(AgentRun.id == UUID(state["run_id"])).with_for_update()
            )
            if run is None:
                raise AgentRunNotFoundError(state["run_id"])
            latest_sequence = await session.scalar(
                select(func.max(AgentStep.sequence_number)).where(AgentStep.run_id == run.id)
            )
            session.add(
                AgentStep(
                    run_id=run.id,
                    sequence_number=int(latest_sequence or 0) + 1,
                    node_name=node_name,
                    status=status.value,
                    state_snapshot=dict(state),
                    error_code=error_code,
                    error_message=error_message,
                    latency_ms=latency_ms,
                    completed_at=datetime.now(UTC),
                )
            )
            self._apply_state(run, state)

    async def update_run(self, state: AgentState) -> None:
        async with self._session_factory() as session, session.begin():
            run = await session.get(AgentRun, UUID(state["run_id"]), with_for_update=True)
            if run is None:
                raise AgentRunNotFoundError(state["run_id"])
            self._apply_state(run, state)

    async def get(self, run_id: UUID) -> StoredAgentRun:
        async with self._session_factory() as session:
            run = await session.get(AgentRun, run_id)
            if run is None:
                raise AgentRunNotFoundError(str(run_id))
            rows = (
                await session.scalars(
                    select(AgentStep)
                    .where(AgentStep.run_id == run_id)
                    .order_by(AgentStep.sequence_number)
                )
            ).all()
            return StoredAgentRun(
                id=run.id,
                request_id=run.request_id,
                conversation_id=run.conversation_id,
                status=AgentRunStatus(run.status),
                intent=run.intent,
                intent_confidence=run.intent_confidence,
                risk_level=run.risk_level,
                current_node=run.current_node,
                state=AgentState(**run.state),
                error_code=run.error_code,
                started_at=run.started_at,
                completed_at=run.completed_at,
                steps=tuple(self._stored_step(row) for row in rows),
            )

    @staticmethod
    def _apply_state(run: AgentRun, state: AgentState) -> None:
        run.conversation_id = _optional_uuid(state["conversation_id"])
        run.status = state["status"]
        run.intent = state["intent"]
        run.intent_confidence = state["intent_confidence"]
        run.risk_level = state["risk_level"]
        run.current_node = state["current_node"]
        run.state = dict(state)
        run.error_code = None if state["error"] is None else state["error"]["code"]
        if state["status"] not in {
            AgentRunStatus.RUNNING.value,
            AgentRunStatus.WAITING_APPROVAL.value,
        }:
            run.completed_at = datetime.now(UTC)
        else:
            run.completed_at = None

    @staticmethod
    def _stored_step(step: AgentStep) -> StoredAgentStep:
        return StoredAgentStep(
            id=step.id,
            sequence_number=step.sequence_number,
            node_name=step.node_name,
            status=AgentStepStatus(step.status),
            state_snapshot=step.state_snapshot,
            error_code=step.error_code,
            error_message=step.error_message,
            latency_ms=step.latency_ms,
            started_at=step.started_at,
            completed_at=step.completed_at,
        )


def _optional_uuid(value: str | None) -> UUID | None:
    return None if value is None else UUID(value)
