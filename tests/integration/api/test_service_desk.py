"""Phase 8 Agent confirmation and local service-desk HTTP contracts."""

from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config
from apps.api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import text

from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


@pytest.fixture
async def service_desk_api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[TestClient]:
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
    with TestClient(create_app(settings=settings)) as client:
        yield client
    get_settings.cache_clear()


@pytest.mark.integration
def test_agent_ticket_request_requires_confirmation_and_duplicate_confirm_replays(
    service_desk_api_client: TestClient,
) -> None:
    response = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Create an IT ticket for my unresolved VPN problem",
            "actor_id": "employee-api-001",
            "user_role": "employee",
            "idempotency_key": "api-create-ticket-once",
        },
        headers={"X-Request-ID": "phase8-api-respond"},
    )

    assert response.status_code == 200
    proposed = response.json()
    assert proposed["run"]["intent"] == "ticket_request"
    assert proposed["pending_confirmation"]["action"] == "create_ticket"
    assert proposed["pending_confirmation"]["risk_level"] == "r1"
    assert proposed["pending_confirmation"]["status"] == "pending"
    confirmation_id = proposed["pending_confirmation"]["id"]
    repeated_respond = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Create an IT ticket for my unresolved VPN problem",
            "actor_id": "employee-api-001",
            "user_role": "employee",
            "idempotency_key": "api-create-ticket-once",
        },
    )
    assert repeated_respond.status_code == 200
    assert repeated_respond.json()["pending_confirmation"]["id"] == confirmation_id

    before = service_desk_api_client.get(
        "/audit/events",
        params={"actor_id": "support-001", "user_role": "it_support"},
    )
    assert before.status_code == 200
    assert any(event["execution_result"] == "not_executed" for event in before.json()["items"])

    first = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-api-001",
            "user_role": "employee",
        },
        headers={"X-Request-ID": "phase8-api-confirm"},
    )
    replay = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-api-001",
            "user_role": "employee",
        },
        headers={"X-Request-ID": "phase8-api-confirm-replay"},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json()["result"] == replay.json()["result"]
    ticket_number = first.json()["result"]["ticket_number"]
    ticket = service_desk_api_client.get(
        f"/tickets/{ticket_number}",
        params={"actor_id": "employee-api-001", "user_role": "employee"},
    )
    assert ticket.status_code == 200
    assert ticket.json()["ticket_number"] == ticket_number
    assert ticket.json()["source_agent_run_id"] == proposed["run"]["run_id"]
    assert ticket.json()["diagnosis_summary"]


@pytest.mark.integration
def test_pending_ticket_action_can_be_cancelled_but_not_executed(
    service_desk_api_client: TestClient,
) -> None:
    proposed = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Create an IT ticket for a VPN issue",
            "actor_id": "employee-cancel-001",
            "user_role": "employee",
            "idempotency_key": "cancel-ticket-once",
        },
    ).json()
    confirmation_id = proposed["pending_confirmation"]["id"]

    wrong_actor = service_desk_api_client.post(
        "/agent/cancel",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-cancel-other",
            "user_role": "employee",
        },
    )
    cancelled = service_desk_api_client.post(
        "/agent/cancel",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-cancel-001",
            "user_role": "employee",
        },
    )
    replay = service_desk_api_client.post(
        "/agent/cancel",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-cancel-001",
            "user_role": "employee",
        },
    )
    confirm_after_cancel = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": confirmation_id,
            "actor_id": "employee-cancel-001",
            "user_role": "employee",
        },
    )
    audit = service_desk_api_client.get(
        "/audit/events",
        params={"actor_id": "support-cancel-audit", "user_role": "it_support"},
    )

    assert wrong_actor.status_code == 403
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None
    assert replay.status_code == 200
    assert replay.json()["id"] == confirmation_id
    assert confirm_after_cancel.status_code == 409
    assert audit.status_code == 200
    cancel_events = [
        event
        for event in audit.json()["items"]
        if event["action"] == "cancel_action"
        and event["target"] == f"pending_confirmation:{confirmation_id}"
    ]
    assert {(event["policy_decision"], event["execution_result"]) for event in cancel_events} == {
        ("allow", "cancelled"),
        ("deny", "not_cancelled"),
    }


@pytest.mark.integration
def test_audit_endpoint_denies_employee_and_failed_diagnosis_proposes_ticket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    settings = Settings(environment=Environment.TEST).model_copy(update={"agent_max_tool_calls": 1})
    with TestClient(create_app(settings=settings)) as client:
        denied = client.get(
            "/audit/events",
            params={"actor_id": "employee-api-002", "user_role": "employee"},
        )
        response = client.post(
            "/agent/respond",
            json={
                "user_message": "VPN cannot connect",
                "actor_id": "employee-api-002",
                "user_role": "employee",
                "idempotency_key": "failed-diagnosis-ticket",
            },
        )
    get_settings.cache_clear()

    assert denied.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    assert payload["run"]["status"] == "escalated"
    assert payload["pending_confirmation"]["action"] == "create_ticket"
    assert payload["pending_confirmation"]["parameters_summary"]["category"] == "vpn"


@pytest.mark.integration
def test_comment_and_r3_requests_preserve_confirmation_and_permission_boundaries(
    service_desk_api_client: TestClient,
) -> None:
    proposed = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Create a ticket for an account issue",
            "actor_id": "employee-api-003",
            "user_role": "employee",
            "idempotency_key": "comment-base-ticket",
        },
    ).json()
    created = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": proposed["pending_confirmation"]["id"],
            "actor_id": "employee-api-003",
            "user_role": "employee",
        },
    ).json()
    ticket_number = created["result"]["ticket_number"]

    comment = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "The account is still locked after another sign-in attempt.",
            "actor_id": "employee-api-003",
            "user_role": "employee",
            "idempotency_key": "comment-api-once",
            "ticket_number": ticket_number,
        },
    )
    assert comment.status_code == 200
    assert comment.json()["pending_confirmation"]["action"] == "add_ticket_comment"
    before = service_desk_api_client.get(
        f"/tickets/{ticket_number}",
        params={"actor_id": "employee-api-003", "user_role": "employee"},
    )
    wrong_actor = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": comment.json()["pending_confirmation"]["id"],
            "actor_id": "employee-api-other",
            "user_role": "employee",
        },
    )
    assert before.status_code == 200
    assert before.json()["comments"] == []
    assert wrong_actor.status_code == 403

    confirmed = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": comment.json()["pending_confirmation"]["id"],
            "actor_id": "employee-api-003",
            "user_role": "employee",
        },
    )
    forbidden_ticket = service_desk_api_client.get(
        f"/tickets/{ticket_number}",
        params={"actor_id": "employee-api-other", "user_role": "employee"},
    )
    after = service_desk_api_client.get(
        f"/tickets/{ticket_number}",
        params={"actor_id": "employee-api-003", "user_role": "employee"},
    )
    assert confirmed.status_code == 200
    assert forbidden_ticket.status_code == 403
    assert len(after.json()["comments"]) == 1

    approval = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Reset password for my account",
            "actor_id": "employee-api-003",
            "user_role": "employee",
            "idempotency_key": "r3-password-approval",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["pending_confirmation"]["risk_level"] == "r3"
    assert approval.json()["pending_confirmation"]["status"] == "approval_required"
    r3_confirm = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": approval.json()["pending_confirmation"]["id"],
            "actor_id": "employee-api-003",
            "user_role": "employee",
        },
    )
    assert r3_confirm.status_code == 409

    permission_approval = service_desk_api_client.post(
        "/agent/respond",
        json={
            "user_message": "Grant access to the finance shared folder",
            "actor_id": "employee-api-003",
            "user_role": "employee",
            "idempotency_key": "r3-permission-approval",
        },
    )
    assert permission_approval.status_code == 200
    assert permission_approval.json()["pending_confirmation"]["action"] == "modify_permissions"
    assert permission_approval.json()["pending_confirmation"]["status"] == "approval_required"
    permission_confirm = service_desk_api_client.post(
        "/agent/confirm",
        json={
            "confirmation_id": permission_approval.json()["pending_confirmation"]["id"],
            "actor_id": "employee-api-003",
            "user_role": "employee",
        },
    )
    assert permission_confirm.status_code == 409
