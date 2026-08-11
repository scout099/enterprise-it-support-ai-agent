"""PostgreSQL repositories for Feedback and bounded analytics aggregates."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.agent_runtime.models import AgentRun
from enterprise_it_support.analytics.domain import (
    FeedbackAccessDeniedError,
    FeedbackConflictError,
    FeedbackCreate,
    FeedbackNotFoundError,
    RawAnalytics,
    StoredFeedback,
)
from enterprise_it_support.analytics.models import Feedback
from enterprise_it_support.service_desk.models import Ticket


class FeedbackRepository:
    """Persist one idempotent feedback record for an owned Agent Run."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, command: FeedbackCreate) -> StoredFeedback:
        async with self._session_factory() as session, session.begin():
            lock_keys = sorted(
                {
                    f"feedback-idempotency:{command.idempotency_key}",
                    f"feedback-run:{command.agent_run_id}",
                }
            )
            for lock_key in lock_keys:
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                    {"key": lock_key},
                )
            run = await session.get(AgentRun, command.agent_run_id)
            if run is None:
                raise FeedbackNotFoundError("Agent Run was not found")
            context = run.state.get("user_context", {})
            if (
                str(context.get("actor_id") or "") != command.actor_id
                or str(context.get("role") or "") != command.user_role
            ):
                raise FeedbackAccessDeniedError("Agent Run does not belong to caller")

            ticket: Ticket | None = None
            if command.ticket_number is not None:
                ticket = await session.scalar(
                    select(Ticket).where(Ticket.ticket_number == command.ticket_number)
                )
                if ticket is None:
                    raise FeedbackNotFoundError("Ticket was not found")
                if (
                    ticket.requester_id != command.actor_id
                    or ticket.source_agent_run_id != command.agent_run_id
                ):
                    raise FeedbackAccessDeniedError("Ticket does not belong to Agent Run")

            existing = await session.scalar(
                select(Feedback).where(
                    (Feedback.agent_run_id == command.agent_run_id)
                    | (Feedback.idempotency_key == command.idempotency_key)
                )
            )
            if existing is not None:
                expected = (
                    command.agent_run_id,
                    command.actor_id,
                    command.resolved,
                    command.satisfaction_rating,
                    command.comment,
                    None if ticket is None else ticket.id,
                    command.idempotency_key,
                )
                actual = (
                    existing.agent_run_id,
                    existing.actor_id,
                    existing.resolved,
                    existing.satisfaction_rating,
                    existing.comment,
                    existing.ticket_id,
                    existing.idempotency_key,
                )
                if actual != expected:
                    raise FeedbackConflictError("Feedback was already submitted with other values")
                return self._stored(existing, command.ticket_number)

            row = Feedback(
                agent_run_id=command.agent_run_id,
                conversation_id=run.conversation_id,
                ticket_id=None if ticket is None else ticket.id,
                actor_id=command.actor_id,
                resolved=command.resolved,
                satisfaction_rating=command.satisfaction_rating,
                comment=command.comment,
                idempotency_key=command.idempotency_key,
            )
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return self._stored(row, command.ticket_number)

    @staticmethod
    def _stored(row: Feedback, ticket_number: str | None) -> StoredFeedback:
        return StoredFeedback(
            id=row.id,
            agent_run_id=row.agent_run_id,
            conversation_id=row.conversation_id,
            ticket_number=ticket_number,
            actor_id=row.actor_id,
            resolved=row.resolved,
            satisfaction_rating=row.satisfaction_rating,
            comment=row.comment,
            idempotency_key=row.idempotency_key,
            created_at=row.created_at,
        )


class AnalyticsRepository:
    """Execute bounded SQL aggregates; presentation shaping belongs to the service."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, *, start: datetime, end: datetime) -> RawAnalytics:
        parameters = {"start": start, "end": end}
        async with self._session_factory() as session:
            summary = dict(
                (
                    await session.execute(
                        text(
                            "WITH runs AS ("
                            " SELECT id, status, started_at, completed_at FROM agent_runs"
                            " WHERE started_at >= :start AND started_at < :end"
                            "), step_counts AS ("
                            " SELECT s.run_id, count(*) AS count FROM agent_steps s"
                            " JOIN runs r ON r.id = s.run_id GROUP BY s.run_id"
                            "), tool_counts AS ("
                            " SELECT t.run_id, count(*) AS count FROM tool_executions t"
                            " JOIN runs r ON r.id = t.run_id GROUP BY t.run_id"
                            ") SELECT count(*) AS total_agent_runs,"
                            " count(*) FILTER (WHERE r.status = 'escalated' OR EXISTS ("
                            "   SELECT 1 FROM tickets t WHERE t.source_agent_run_id = r.id"
                            " )) AS transferred_runs,"
                            " avg(coalesce(sc.count, 0)) AS average_agent_steps,"
                            " avg(coalesce(tc.count, 0)) AS average_tool_calls,"
                            " avg(extract(epoch FROM (r.completed_at - r.started_at)) * 1000)"
                            "   FILTER (WHERE r.completed_at IS NOT NULL)"
                            "   AS average_response_time_ms,"
                            " count(r.completed_at) AS response_time_samples"
                            " FROM runs r LEFT JOIN step_counts sc ON sc.run_id = r.id"
                            " LEFT JOIN tool_counts tc ON tc.run_id = r.id"
                        ),
                        parameters,
                    )
                )
                .mappings()
                .one()
            )
            ticket_summary = (
                (
                    await session.execute(
                        text(
                            "SELECT count(*) AS total_tickets FROM tickets "
                            "WHERE created_at >= :start AND created_at < :end"
                        ),
                        parameters,
                    )
                )
                .mappings()
                .one()
            )
            feedback_summary = (
                (
                    await session.execute(
                        text(
                            "SELECT count(*) AS feedback_count,"
                            " count(*) FILTER (WHERE resolved AND NOT EXISTS ("
                            "   SELECT 1 FROM tickets t"
                            "   WHERE t.source_agent_run_id = feedback.agent_run_id"
                            " ))"
                            "   AS self_service_resolved,"
                            " avg(satisfaction_rating)"
                            " FILTER (WHERE satisfaction_rating IS NOT NULL)"
                            "   AS average_satisfaction,"
                            " count(satisfaction_rating) AS satisfaction_samples"
                            " FROM feedback WHERE created_at >= :start AND created_at < :end"
                        ),
                        parameters,
                    )
                )
                .mappings()
                .one()
            )
            tool_summary = (
                (
                    await session.execute(
                        text(
                            "SELECT count(*) AS tool_count,"
                            " count(*) FILTER (WHERE status = 'succeeded') AS successful_tools"
                            " FROM tool_executions WHERE started_at >= :start AND started_at < :end"
                        ),
                        parameters,
                    )
                )
                .mappings()
                .one()
            )
            summary.update(dict(ticket_summary))
            summary.update(dict(feedback_summary))
            summary.update(dict(tool_summary))
            ticket_categories = await self._rows(
                session,
                "SELECT category AS label, count(*) AS count FROM tickets "
                "WHERE created_at >= :start AND created_at < :end "
                "GROUP BY category ORDER BY count DESC, category",
                parameters,
            )
            issue_counts = await self._rows(
                session,
                "SELECT intent AS label, count(*) AS count FROM agent_runs "
                "WHERE started_at >= :start AND started_at < :end "
                "AND intent IN ('vpn_diagnosis', 'outlook_diagnosis', 'account_diagnosis') "
                "GROUP BY intent ORDER BY count DESC, intent",
                parameters,
            )
            satisfaction_distribution = await self._rows(
                session,
                "SELECT satisfaction_rating::text AS label, count(*) AS count FROM feedback "
                "WHERE created_at >= :start AND created_at < :end "
                "AND satisfaction_rating IS NOT NULL GROUP BY satisfaction_rating "
                "ORDER BY satisfaction_rating",
                parameters,
            )
            failure_reasons = await self._rows(
                session,
                "SELECT reason AS label, count(*) AS count FROM ("
                " SELECT error_code AS reason FROM agent_runs"
                " WHERE started_at >= :start AND started_at < :end AND error_code IS NOT NULL"
                " UNION ALL SELECT error_code AS reason FROM tool_executions"
                " WHERE started_at >= :start AND started_at < :end AND error_code IS NOT NULL"
                ") failures GROUP BY reason ORDER BY count DESC, reason LIMIT 10",
                parameters,
            )
        return RawAnalytics(
            summary=summary,
            ticket_categories=ticket_categories,
            issue_counts=issue_counts,
            satisfaction_distribution=satisfaction_distribution,
            failure_reasons=failure_reasons,
        )

    @staticmethod
    async def _rows(
        session: AsyncSession,
        statement: str,
        parameters: dict[str, datetime],
    ) -> tuple[dict[str, Any], ...]:
        rows = (await session.execute(text(statement), parameters)).mappings().all()
        return tuple(dict(row) for row in rows)
