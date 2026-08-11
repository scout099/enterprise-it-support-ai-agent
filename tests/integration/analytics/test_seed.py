"""The Phase 11 demo seed is deterministic and idempotent in PostgreSQL."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from apps.dependencies import build_knowledge_retriever
from scripts.seed_phase11_demo import seed_demo_data
from sqlalchemy import text

from enterprise_it_support.analytics.persistence import AnalyticsRepository
from enterprise_it_support.analytics.service import AnalyticsService
from enterprise_it_support.knowledge.retrieval import SearchFilters, UserContext
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


@pytest.mark.integration
async def test_phase11_seed_is_idempotent_and_populates_dashboard_tables(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory.begin() as session:
        await session.execute(
            text(
                "TRUNCATE feedback, audit_events, tool_executions, pending_confirmations, "
                "ticket_comments, tickets, agent_steps, agent_runs, messages, "
                "conversations CASCADE"
            )
        )
    await database.close()

    fixed_now = datetime(2026, 8, 1, 12, tzinfo=UTC)
    first = await seed_demo_data(settings, now=fixed_now)
    second = await seed_demo_data(settings, now=fixed_now)

    database = DatabaseManager(settings.active_database_url)
    try:
        async with database.session_factory() as session:
            statements = {
                "agent_runs": "SELECT count(*) FROM agent_runs",
                "agent_steps": "SELECT count(*) FROM agent_steps",
                "tool_executions": "SELECT count(*) FROM tool_executions",
                "tickets": "SELECT count(*) FROM tickets",
                "feedback": "SELECT count(*) FROM feedback",
            }
            counts = {
                table: int(await session.scalar(text(statement)) or 0)
                for table, statement in statements.items()
            }
        analytics = AnalyticsService(
            AnalyticsRepository(database.session_factory),
            tmp_path / "evaluations",
        )
        summary = await analytics.summary(
            days=30,
            evaluation_limit=5,
            now=fixed_now + timedelta(hours=1),
        )
        oldest_run_boundary = await analytics.summary(
            days=1,
            evaluation_limit=5,
            now=fixed_now - timedelta(days=12) + timedelta(milliseconds=5),
        )
        retriever = build_knowledge_retriever(settings, database.session_factory)
        knowledge = await retriever.search(
            "How do I configure the company VPN?",
            5,
            SearchFilters(),
            UserContext(role="employee"),
        )
    finally:
        await database.close()
        get_settings.cache_clear()

    assert (
        first
        == second
        == {
            "agent_runs": 6,
            "agent_steps": 23,
            "tool_executions": 6,
            "tickets": 4,
            "feedback": 4,
        }
    )
    assert counts == first
    assert summary.total_agent_runs == 6
    assert summary.total_tickets == 4
    assert {item.label: item.count for item in summary.ticket_categories} == {
        "account": 1,
        "other": 1,
        "outlook": 1,
        "vpn": 1,
    }
    assert {item.label: item.count for item in summary.issue_counts} == {
        "Account": 1,
        "Outlook": 2,
        "VPN": 2,
    }
    assert summary.self_service_resolution_rate.value == pytest.approx(0.5)
    assert summary.human_transfer_rate.value == pytest.approx(4 / 6)
    assert summary.average_agent_steps.value == pytest.approx(23 / 6)
    assert summary.average_tool_calls.value == pytest.approx(1.0)
    assert summary.average_response_time_ms.value == pytest.approx(1340 / 6)
    assert summary.tool_success_rate.value == pytest.approx(5 / 6)
    assert summary.average_satisfaction.value == pytest.approx(3.5)
    assert {item.label: item.count for item in summary.frequent_failure_reasons} == {
        "diagnostic_unavailable": 1,
        "mock_timeout": 1,
    }
    assert oldest_run_boundary.total_agent_runs == 1
    assert oldest_run_boundary.average_agent_steps.value == pytest.approx(5.0)
    assert oldest_run_boundary.average_tool_calls.value == pytest.approx(2.0)
    assert any(
        result.citation.document_title == "Evaluation VPN Configuration SOP" for result in knowledge
    )
