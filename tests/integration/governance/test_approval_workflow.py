"""End-to-end local RBAC, approval, checkpoint, and resume behavior."""

from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config
from apps.api.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import text

from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

HIGH_RISK_MESSAGE = "申请加入财务系统管理员组"


@pytest.fixture
async def governance_client(
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
                "TRUNCATE approval_decisions, approval_requests, audit_events, "
                "tool_executions, pending_confirmations, ticket_comments, tickets, "
                "agent_steps, agent_runs, messages, conversations CASCADE"
            )
        )
    await database.close()
    with TestClient(create_app(settings=settings)) as client:
        yield client
    get_settings.cache_clear()


def _request_approval(
    client: TestClient,
    *,
    idempotency_key: str,
    justification: str = "负责季度结账期间的财务系统故障支持。",
    actor_id: str = "employee-demo",
    user_role: str = "employee",
) -> dict[str, object]:
    response = client.post(
        "/agent/respond",
        json={
            "user_message": HIGH_RISK_MESSAGE,
            "actor_id": actor_id,
            "user_role": user_role,
            "idempotency_key": idempotency_key,
            "business_justification": justification,
        },
        headers={"X-Request-ID": f"phase9-{idempotency_key}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_r3_collects_reason_then_pauses_and_approver_resumes_without_reexecution(
    governance_client: TestClient,
) -> None:
    missing = governance_client.post(
        "/agent/respond",
        json={
            "user_message": HIGH_RISK_MESSAGE,
            "actor_id": "employee-demo",
            "user_role": "employee",
            "idempotency_key": "phase9-missing-reason",
        },
    )

    assert missing.status_code == 200
    assert missing.json()["run"]["status"] == "needs_clarification"
    assert missing.json()["run"]["governance_policy_decision"] == "need_more_context"
    assert missing.json()["run"]["approval_request_id"] is None

    proposed = _request_approval(
        governance_client,
        idempotency_key="phase9-approve-once",
    )
    run = proposed["run"]
    assert run["status"] == "waiting_approval"
    assert run["intent"] is None
    assert run["classification_metadata"] is None
    assert run["governance_risk_level"] == "r3"
    assert run["governance_policy_decision"] == "require_approval"
    approval_id = run["approval_request_id"]
    initial_nodes = [step["node_name"] for step in run["steps"]]
    assert initial_nodes == [
        "intake",
        "evaluate_governance_policy",
        "create_approval_request",
    ]

    employee_queue = governance_client.get(
        "/approvals/pending",
        params={"actor_id": "employee-demo"},
    )
    approver_queue = governance_client.get(
        "/approvals/pending",
        params={"actor_id": "approver-demo"},
    )
    assert employee_queue.status_code == 403
    assert approver_queue.status_code == 200
    assert [item["id"] for item in approver_queue.json()["items"]] == [approval_id]

    denied_actor = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "employee-demo", "rationale": "self approval"},
        headers={"X-Request-ID": "phase9-denied-approver"},
    )
    assert denied_actor.status_code == 403

    self_proposed = _request_approval(
        governance_client,
        idempotency_key="phase9-self-approval",
        actor_id="approver-demo",
        user_role="approver",
    )
    self_denied = governance_client.post(
        f"/approvals/{self_proposed['run']['approval_request_id']}/approve",
        json={"actor_id": "approver-demo", "rationale": "self approval is forbidden"},
        headers={"X-Request-ID": "phase9-self-approval-denied"},
    )
    assert self_denied.status_code == 403

    denied_audit = governance_client.get(
        "/audit/events",
        params={"actor_id": "support-demo", "user_role": "it_support"},
    )
    assert any(
        event["actor"] == "employee-demo"
        and event["action"] == "approve_approval"
        and event["policy_decision"] == "deny"
        and event["execution_result"] == "not_executed:access_denied"
        and event["request_id"] == "phase9-denied-approver"
        for event in denied_audit.json()["items"]
    )
    assert any(
        event["actor"] == "employee-demo"
        and event["action"] == "list_pending_approvals"
        and event["policy_decision"] == "deny"
        for event in denied_audit.json()["items"]
    )
    assert any(
        event["actor"] == "approver-demo"
        and event["action"] == "approve_approval"
        and event["execution_result"] == "not_executed:access_denied"
        and event["request_id"] == "phase9-self-approval-denied"
        for event in denied_audit.json()["items"]
    )

    approved = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "approver-demo",
            "rationale": "Business reason verified for the quarter-end window.",
        },
        headers={"X-Request-ID": "phase9-approve"},
    )
    assert approved.status_code == 200, approved.text
    outcome = approved.json()
    assert outcome["approval"]["status"] == "executed"
    assert outcome["approval"]["resumed_at"] is not None
    assert outcome["approval"]["decision"]["decision"] == "approve"
    assert outcome["approval"]["simulated_result"] == {
        "status": "simulated_success",
        "message": "模拟执行成功; 未修改任何真实权限系统。",
        "external_system_modified": False,
    }
    assert outcome["run"]["status"] == "completed"
    assert outcome["run"]["approval_decision"] == "approve"
    nodes = [step["node_name"] for step in outcome["run"]["steps"]]
    assert nodes == [
        "intake",
        "evaluate_governance_policy",
        "create_approval_request",
        "await_human_approval",
        "simulate_approved_action",
        "finalize",
    ]
    assert nodes.count("intake") == 1
    assert nodes.count("evaluate_governance_policy") == 1
    assert nodes.count("create_approval_request") == 1

    approval_audit = governance_client.get(
        "/audit/events",
        params={"actor_id": "support-demo", "user_role": "it_support"},
    )
    approval_events = approval_audit.json()["items"]
    assert any(
        event["action"] == "approve_approval" and event["execution_result"] == "approved"
        for event in approval_events
    )
    assert any(
        event["action"] == "join_finance_admin_group"
        and event["execution_result"] == "simulated_success"
        for event in approval_events
    )
    assert any(
        event["action"] == "resume_approval_run"
        and event["execution_result"] == "completed:approve"
        for event in approval_events
    )

    repeated = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "approver-demo", "rationale": "duplicate"},
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "approval_already_decided"


@pytest.mark.integration
def test_rejection_resumes_original_run_and_ends_without_simulated_execution(
    governance_client: TestClient,
) -> None:
    proposed = _request_approval(
        governance_client,
        idempotency_key="phase9-reject-once",
    )
    approval_id = proposed["run"]["approval_request_id"]

    rejected = governance_client.post(
        f"/approvals/{approval_id}/reject",
        json={
            "actor_id": "approver-demo",
            "rationale": "Least privilege review did not support the request.",
        },
        headers={"X-Request-ID": "phase9-reject"},
    )

    assert rejected.status_code == 200, rejected.text
    outcome = rejected.json()
    assert outcome["approval"]["status"] == "rejected"
    assert outcome["approval"]["resumed_at"] is not None
    assert outcome["approval"]["decision"]["decision"] == "reject"
    assert outcome["approval"]["simulated_result"] is None
    assert outcome["run"]["status"] == "completed"
    assert outcome["run"]["approval_decision"] == "reject"
    assert outcome["run"]["simulated_execution"] is None
    assert [step["node_name"] for step in outcome["run"]["steps"]][-3:] == [
        "await_human_approval",
        "finish_rejected_action",
        "finalize",
    ]

    audit = governance_client.get(
        "/audit/events",
        params={"actor_id": "support-demo", "user_role": "it_support"},
    )
    assert audit.status_code == 200
    events = audit.json()["items"]
    assert any(
        event["action"] == "join_finance_admin_group"
        and event["policy_decision"] == "require_approval"
        and event["execution_result"] == "pending_human_approval"
        for event in events
    )
    assert any(
        event["action"] == "reject_approval"
        and event["policy_decision"] == "deny"
        and event["execution_result"] == "rejected"
        for event in events
    )


@pytest.mark.integration
def test_same_persisted_decision_can_resume_after_runtime_failure_once(
    governance_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposed = _request_approval(
        governance_client,
        idempotency_key="phase9-resume-recovery",
    )
    run_id = proposed["run"]["run_id"]
    approval_id = proposed["run"]["approval_request_id"]
    runtime = governance_client.app.state.agent_runtime
    real_resume = runtime.resume

    async def unavailable_resume(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected checkpoint outage")

    monkeypatch.setattr(runtime, "resume", unavailable_resume)
    failed = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "approver-demo",
            "rationale": "Verified recovery test decision.",
        },
        headers={"X-Request-ID": "phase9-resume-failed"},
    )

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "service_unavailable"
    assert governance_client.app.state.governance_service is not None

    monkeypatch.setattr(runtime, "resume", real_resume)
    different_approver = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "admin-demo",
            "rationale": "Verified recovery test decision.",
        },
    )
    changed_decision = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "approver-demo",
            "rationale": "A different rationale must not replace the saved decision.",
        },
    )
    assert different_approver.status_code == 403
    assert changed_decision.status_code == 409

    recovered = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "approver-demo",
            "rationale": "Verified recovery test decision.",
        },
        headers={"X-Request-ID": "phase9-resume-recovered"},
    )

    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["run"]["run_id"] == run_id
    assert recovered.json()["run"]["status"] == "completed"
    assert recovered.json()["approval"]["status"] == "executed"
    assert recovered.json()["approval"]["resumed_at"] is not None
    nodes = [step["node_name"] for step in recovered.json()["run"]["steps"]]
    assert nodes.count("intake") == 1
    assert nodes.count("evaluate_governance_policy") == 1
    assert nodes.count("create_approval_request") == 1

    recovery_audit = governance_client.get(
        "/audit/events",
        params={"actor_id": "support-demo", "user_role": "it_support"},
    ).json()["items"]
    assert any(
        event["action"] == "resume_approval_run"
        and event["execution_result"] == "failed:runtime_unavailable"
        and event["request_id"] == "phase9-resume-failed"
        for event in recovery_audit
    )
    assert any(
        event["action"] == "resume_approval_run"
        and event["execution_result"] == "completed:approve"
        and event["request_id"] == "phase9-resume-recovered"
        for event in recovery_audit
    )

    duplicate = governance_client.post(
        f"/approvals/{approval_id}/approve",
        json={
            "actor_id": "approver-demo",
            "rationale": "Verified recovery test decision.",
        },
    )
    assert duplicate.status_code == 409
