"""Idempotently seed fixed fictional rows for the Phase 11 local dashboard demo."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import text

from enterprise_it_support.evaluation.fixtures import seed_evaluation_fixtures
from enterprise_it_support.platform.config import EmbeddingProviderType, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

NAMESPACE = UUID("2bb73011-51a8-4e1d-8e5c-d30c75db4038")
ACTOR_ID = "phase11-demo-employee"


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


async def seed_demo_data(settings: Settings, *, now: datetime | None = None) -> dict[str, int]:
    """Insert only deterministic fictional records; repeated calls do not duplicate them."""
    if settings.embedding_provider is not EmbeddingProviderType.FAKE:
        raise RuntimeError("Phase 11 demo seed requires the fake embedding provider")
    current = now or datetime.now(UTC)
    database = DatabaseManager(settings.active_database_url)
    runs = _run_rows(current)
    steps = _step_rows(runs)
    tools = _tool_rows(runs)
    tickets = _ticket_rows(runs, current)
    feedback = _feedback_rows(runs, tickets, current)
    try:
        await seed_evaluation_fixtures(settings, database)
        async with database.session_factory() as session, session.begin():
            await session.execute(
                text(
                    "INSERT INTO agent_runs "
                    "(id, request_id, conversation_id, status, intent, intent_confidence, "
                    "risk_level, current_node, state, error_code, started_at, completed_at) "
                    "VALUES (:id, :request_id, NULL, :status, :intent, :intent_confidence, "
                    ":risk_level, :current_node, CAST(:state AS jsonb), :error_code, "
                    ":started_at, :completed_at) ON CONFLICT (id) DO NOTHING"
                ),
                runs,
            )
            await session.execute(
                text(
                    "INSERT INTO agent_steps "
                    "(id, run_id, sequence_number, node_name, status, state_snapshot, "
                    "error_code, error_message, latency_ms, started_at, completed_at) "
                    "VALUES (:id, :run_id, :sequence_number, :node_name, :status, "
                    "CAST(:state_snapshot AS jsonb), :error_code, NULL, :latency_ms, "
                    ":started_at, :completed_at) ON CONFLICT (id) DO NOTHING"
                ),
                steps,
            )
            await session.execute(
                text(
                    "INSERT INTO tool_executions "
                    "(id, run_id, actor_id, pending_confirmation_id, idempotency_key, "
                    "request_id, node_name, tool_name, tool_version, status, input_arguments, "
                    "observation, required_risk_level, has_side_effect, error_code, "
                    "error_message, attempts, latency_ms, started_at, completed_at) "
                    "VALUES (:id, :run_id, :actor_id, NULL, NULL, :request_id, :node_name, "
                    ":tool_name, '1.0.0', :status, CAST(:input_arguments AS jsonb), "
                    "CAST(:observation AS jsonb), 'r0', false, :error_code, NULL, 1, "
                    ":latency_ms, :started_at, :completed_at) ON CONFLICT (id) DO NOTHING"
                ),
                tools,
            )
            await session.execute(
                text(
                    "INSERT INTO tickets "
                    "(id, ticket_number, title, description, category, priority, status, "
                    "requester_id, assigned_to, source_conversation_id, source_agent_run_id, "
                    "diagnosis_summary, idempotency_key, created_at, updated_at) "
                    "VALUES (:id, :ticket_number, :title, :description, :category, :priority, "
                    ":status, :requester_id, NULL, NULL, :source_agent_run_id, "
                    ":diagnosis_summary, :idempotency_key, :created_at, :updated_at) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                tickets,
            )
            await session.execute(
                text(
                    "INSERT INTO feedback "
                    "(id, agent_run_id, conversation_id, ticket_id, actor_id, resolved, "
                    "satisfaction_rating, comment, idempotency_key, created_at) "
                    "VALUES (:id, :agent_run_id, NULL, :ticket_id, :actor_id, :resolved, "
                    ":satisfaction_rating, :comment, :idempotency_key, :created_at) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                feedback,
            )
    finally:
        await database.close()
    return {
        "agent_runs": len(runs),
        "agent_steps": len(steps),
        "tool_executions": len(tools),
        "tickets": len(tickets),
        "feedback": len(feedback),
    }


def _run_rows(now: datetime) -> list[dict[str, Any]]:
    definitions = [
        ("vpn", "vpn_diagnosis", "completed", None, 5, 180),
        ("outlook", "outlook_diagnosis", "completed", None, 4, 240),
        ("account", "account_diagnosis", "completed", None, 3, 120),
        ("ticket", "ticket_request", "completed", None, 3, 90),
        ("escalated", "vpn_diagnosis", "escalated", None, 4, 310),
        ("failed", "outlook_diagnosis", "failed", "diagnostic_unavailable", 4, 400),
    ]
    rows: list[dict[str, Any]] = []
    for index, (name, intent, status, error_code, _, latency_ms) in enumerate(definitions):
        started_at = now - timedelta(days=12 - index)
        rows.append(
            {
                "id": _id(f"run-{name}"),
                "request_id": f"phase11-seed-{name}",
                "status": status,
                "intent": intent,
                "intent_confidence": 0.95,
                "risk_level": "low",
                "current_node": "finalize",
                "state": json.dumps(
                    {
                        "user_context": {"actor_id": ACTOR_ID, "role": "employee"},
                        "seed": "phase11-fictional-demo",
                    }
                ),
                "error_code": error_code,
                "started_at": started_at,
                "completed_at": started_at + timedelta(milliseconds=latency_ms),
                "step_count": definitions[index][4],
                "name": name,
            }
        )
    return rows


def _step_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in runs:
        for sequence in range(1, int(run["step_count"]) + 1):
            started_at = run["started_at"] + timedelta(milliseconds=sequence * 10)
            rows.append(
                {
                    "id": _id(f"step-{run['name']}-{sequence}"),
                    "run_id": run["id"],
                    "sequence_number": sequence,
                    "node_name": (
                        "finalize" if sequence == run["step_count"] else f"step_{sequence}"
                    ),
                    "status": (
                        "failed" if run["name"] == "failed" and sequence == 3 else "succeeded"
                    ),
                    "state_snapshot": json.dumps({"seed": True, "sequence": sequence}),
                    "error_code": (
                        "diagnostic_unavailable"
                        if run["name"] == "failed" and sequence == 3
                        else None
                    ),
                    "latency_ms": 10 + sequence,
                    "started_at": started_at,
                    "completed_at": started_at + timedelta(milliseconds=10 + sequence),
                }
            )
    return rows


def _tool_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {str(run["name"]): run for run in runs}
    definitions = [
        ("vpn", "check_vpn_service", "succeeded", None, 24),
        ("vpn", "get_device_info", "succeeded", None, 18),
        ("outlook", "check_mail_service", "succeeded", None, 30),
        ("account", "check_account_status", "succeeded", None, 20),
        ("escalated", "check_vpn_service", "succeeded", None, 27),
        ("failed", "check_mail_service", "timed_out", "mock_timeout", 80),
    ]
    rows = []
    for index, (run_name, tool_name, status, error_code, latency_ms) in enumerate(definitions):
        run = by_name[run_name]
        started_at = run["started_at"] + timedelta(milliseconds=40)
        rows.append(
            {
                "id": _id(f"tool-{index}-{run_name}-{tool_name}"),
                "run_id": run["id"],
                "actor_id": ACTOR_ID,
                "request_id": run["request_id"],
                "node_name": f"seed_{tool_name}",
                "tool_name": tool_name,
                "status": status,
                "input_arguments": json.dumps({"seed": "fictional"}),
                "observation": json.dumps({"healthy": status == "succeeded"}),
                "error_code": error_code,
                "latency_ms": latency_ms,
                "started_at": started_at,
                "completed_at": started_at + timedelta(milliseconds=latency_ms),
            }
        )
    return rows


def _ticket_rows(runs: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    by_name = {str(run["name"]): run for run in runs}
    definitions = [
        ("ticket", "VPN", "vpn", "open"),
        ("escalated", "Outlook", "outlook", "in_progress"),
        ("failed", "Account", "account", "resolved"),
        ("vpn", "Other", "other", "closed"),
    ]
    rows = []
    for index, (run_name, title, category, status) in enumerate(definitions, start=1):
        run = by_name[run_name]
        rows.append(
            {
                "id": _id(f"ticket-{category}-{index}"),
                "ticket_number": f"IT-DEMO-11-{index:03d}",
                "title": f"Fictional {title} demo ticket",
                "description": "Fixed fictional Phase 11 dashboard seed data.",
                "category": category,
                "priority": "medium",
                "status": status,
                "requester_id": ACTOR_ID,
                "source_agent_run_id": run["id"],
                "diagnosis_summary": '{"seed":"phase11-fictional-demo"}',
                "idempotency_key": f"phase11-seed-ticket-{index}",
                "created_at": now - timedelta(days=9 - index),
                "updated_at": now - timedelta(days=8 - index),
            }
        )
    return rows


def _feedback_rows(
    runs: list[dict[str, Any]],
    tickets: list[dict[str, Any]],
    now: datetime,
) -> list[dict[str, Any]]:
    by_name = {str(run["name"]): run for run in runs}
    ticket_by_run = {ticket["source_agent_run_id"]: ticket for ticket in tickets}
    definitions = [
        ("account", True, 5, False),
        ("outlook", True, 4, False),
        ("ticket", False, 2, True),
        ("failed", False, 3, True),
    ]
    rows = []
    for index, (run_name, resolved, rating, with_ticket) in enumerate(definitions, start=1):
        run = by_name[run_name]
        ticket = ticket_by_run.get(run["id"]) if with_ticket else None
        rows.append(
            {
                "id": _id(f"feedback-{run_name}"),
                "agent_run_id": run["id"],
                "ticket_id": None if ticket is None else ticket["id"],
                "actor_id": ACTOR_ID,
                "resolved": resolved,
                "satisfaction_rating": rating,
                "comment": "Fixed fictional Phase 11 feedback.",
                "idempotency_key": f"phase11-seed-feedback-{index}",
                "created_at": now - timedelta(days=5 - index),
            }
        )
    return rows


async def _main() -> None:
    counts = await seed_demo_data(get_settings())
    print(json.dumps({"seed": "phase11-fictional-demo", **counts}, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
