"""Phase 11 Feedback and Analytics HTTP contracts against PostgreSQL."""

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from apps.api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import text

from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


@pytest.fixture
async def analytics_api_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> AsyncIterator[TestClient]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    artifact_path = tmp_path / "evaluations"
    artifact_path.mkdir()
    (artifact_path / "eval-phase11-demo.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "run_id": "eval-phase11-demo",
                    "created_at": "2026-08-01T12:00:00Z",
                    "dataset_version": "phase-10-v1",
                },
                "metrics": {
                    "agent": {
                        "intent_accuracy": {"value": 1.0},
                        "workflow_completion_rate": {"value": 0.95},
                    },
                    "generation": {"citation_validity": {"value": 1.0}},
                },
                "gate": {"passed": True},
                "failed_case_ids": ["knowledge-07"],
            }
        ),
        encoding="utf-8",
    )
    (artifact_path / "eval-malformed.json").write_text("{", encoding="utf-8")
    settings = Settings(environment=Environment.TEST).model_copy(
        update={"evaluation_artifacts_path": artifact_path}
    )
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
    with TestClient(create_app(settings=settings)) as client:
        yield client
    get_settings.cache_clear()


@pytest.mark.integration
def test_feedback_is_idempotent_owned_and_drives_backend_analytics(
    analytics_api_client: TestClient,
) -> None:
    self_service = analytics_api_client.post(
        "/agent/respond",
        json={
            "user_message": "My account is locked",
            "actor_id": "analytics-employee-001",
            "user_role": "employee",
            "idempotency_key": "analytics-account-run",
        },
    ).json()
    self_service_feedback = {
        "agent_run_id": self_service["run"]["run_id"],
        "actor_id": "analytics-employee-001",
        "user_role": "employee",
        "resolved": True,
        "satisfaction_rating": 5,
        "comment": "The guided checks resolved the fictional demo issue.",
        "idempotency_key": "analytics-feedback-self-service",
    }
    created = analytics_api_client.post("/feedback", json=self_service_feedback)
    replay = analytics_api_client.post("/feedback", json=self_service_feedback)
    conflicting = analytics_api_client.post(
        "/feedback",
        json={**self_service_feedback, "resolved": False},
    )
    wrong_actor = analytics_api_client.post(
        "/feedback",
        json={
            **self_service_feedback,
            "actor_id": "analytics-employee-other",
            "idempotency_key": "analytics-feedback-wrong-actor",
        },
    )

    ticket_run = analytics_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Create an IT ticket for my unresolved VPN issue",
            "actor_id": "analytics-employee-002",
            "user_role": "employee",
            "idempotency_key": "analytics-ticket-run",
        },
    ).json()
    confirmation = analytics_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": ticket_run["pending_confirmation"]["id"],
            "actor_id": "analytics-employee-002",
            "user_role": "employee",
        },
    ).json()
    ticket_number = confirmation["result"]["ticket_number"]
    ticket_feedback = analytics_api_client.post(
        "/feedback",
        json={
            "agent_run_id": ticket_run["run"]["run_id"],
            "actor_id": "analytics-employee-002",
            "user_role": "employee",
            "resolved": False,
            "satisfaction_rating": 2,
            "ticket_number": ticket_number,
            "idempotency_key": "analytics-feedback-ticket",
        },
    )
    other_run = analytics_api_client.post(
        "/agent/respond",
        json={
            "user_message": "My account is locked",
            "actor_id": "analytics-employee-003",
            "user_role": "employee",
            "idempotency_key": "analytics-other-run",
        },
    ).json()
    reused_global_key = analytics_api_client.post(
        "/feedback",
        json={
            "agent_run_id": other_run["run"]["run_id"],
            "actor_id": "analytics-employee-003",
            "user_role": "employee",
            "resolved": True,
            "idempotency_key": "analytics-feedback-self-service",
        },
    )
    missing_ticket = analytics_api_client.post(
        "/feedback",
        json={
            "agent_run_id": other_run["run"]["run_id"],
            "actor_id": "analytics-employee-003",
            "user_role": "employee",
            "resolved": False,
            "ticket_number": "IT-NOT-FOUND",
            "idempotency_key": "analytics-feedback-missing-ticket",
        },
    )
    mismatched_ticket = analytics_api_client.post(
        "/feedback",
        json={
            "agent_run_id": other_run["run"]["run_id"],
            "actor_id": "analytics-employee-003",
            "user_role": "employee",
            "resolved": False,
            "ticket_number": ticket_number,
            "idempotency_key": "analytics-feedback-mismatched-ticket",
        },
    )

    denied = analytics_api_client.get(
        "/analytics/summary",
        params={"actor_id": "analytics-employee-001", "user_role": "employee"},
    )
    dashboard = analytics_api_client.get(
        "/analytics/summary",
        params={"actor_id": "support-demo", "user_role": "it_support"},
    )

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == created.json()["id"]
    assert conflicting.status_code == 409
    assert wrong_actor.status_code == 403
    assert ticket_feedback.status_code == 201
    assert reused_global_key.status_code == 409
    assert missing_ticket.status_code == 404
    assert mismatched_ticket.status_code == 403
    assert denied.status_code == 403
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["total_agent_runs"] == 3
    assert payload["total_tickets"] == 1
    assert {item["label"]: item["count"] for item in payload["ticket_categories"]} == {"vpn": 1}
    assert {item["label"]: item["count"] for item in payload["issue_counts"]} == {"Account": 2}
    assert payload["self_service_resolution_rate"] == {"value": 0.5, "sample_count": 2}
    assert payload["human_transfer_rate"] == {"value": 1 / 3, "sample_count": 3}
    assert payload["average_agent_steps"]["value"] > 0
    assert payload["average_tool_calls"]["value"] > 0
    assert payload["average_response_time_ms"]["value"] >= 0
    assert payload["tool_success_rate"]["value"] == 1.0
    assert payload["average_satisfaction"] == {"value": 3.5, "sample_count": 2}
    assert payload["recent_evaluations"] == [
        {
            "run_id": "eval-phase11-demo",
            "created_at": "2026-08-01T12:00:00Z",
            "gate_passed": True,
            "dataset_version": "phase-10-v1",
            "intent_accuracy": 1.0,
            "workflow_completion_rate": 0.95,
            "citation_validity": 1.0,
            "failed_case_count": 1,
        }
    ]


@pytest.mark.integration
def test_empty_analytics_preserves_n_a_metrics(
    analytics_api_client: TestClient,
) -> None:
    response = analytics_api_client.get(
        "/analytics/summary",
        params={"actor_id": "support-empty", "user_role": "project_maintainer"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_agent_runs"] == 0
    assert payload["total_tickets"] == 0
    assert payload["ticket_categories"] == []
    assert payload["issue_counts"] == []
    assert payload["satisfaction_distribution"] == []
    assert payload["frequent_failure_reasons"] == []
    for name in (
        "self_service_resolution_rate",
        "human_transfer_rate",
        "average_agent_steps",
        "average_tool_calls",
        "average_response_time_ms",
        "tool_success_rate",
        "average_satisfaction",
    ):
        assert payload[name] == {"value": None, "sample_count": 0}
    assert [item["run_id"] for item in payload["recent_evaluations"]] == ["eval-phase11-demo"]
