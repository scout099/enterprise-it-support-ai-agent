"""Knowledge schema migration tests against PostgreSQL."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from enterprise_it_support.platform.config import Environment, Settings, get_settings

EXPECTED_COLUMNS = {
    "feedback": {
        "id",
        "agent_run_id",
        "conversation_id",
        "ticket_id",
        "actor_id",
        "resolved",
        "satisfaction_rating",
        "comment",
        "idempotency_key",
        "created_at",
    },
    "users": {
        "id",
        "external_id",
        "display_name",
        "is_active",
        "created_at",
    },
    "roles": {"id", "name", "description", "created_at"},
    "permissions": {"id", "name", "description", "created_at"},
    "user_roles": {"user_id", "role_id", "assigned_at"},
    "role_permissions": {"role_id", "permission_id", "assigned_at"},
    "approval_requests": {
        "id",
        "requester_user_id",
        "action",
        "tool",
        "target_resource",
        "risk_level",
        "business_justification",
        "request_context",
        "policy_decision",
        "status",
        "idempotency_key",
        "source_agent_run_id",
        "checkpoint_node",
        "simulated_result",
        "created_at",
        "decided_at",
        "executed_at",
        "resumed_at",
    },
    "approval_decisions": {
        "id",
        "approval_request_id",
        "approver_user_id",
        "decision",
        "rationale",
        "decided_at",
    },
    "tool_executions": {
        "id",
        "run_id",
        "actor_id",
        "pending_confirmation_id",
        "idempotency_key",
        "request_id",
        "node_name",
        "tool_name",
        "tool_version",
        "status",
        "input_arguments",
        "observation",
        "required_risk_level",
        "has_side_effect",
        "error_code",
        "error_message",
        "attempts",
        "latency_ms",
        "started_at",
        "completed_at",
    },
    "tickets": {
        "id",
        "ticket_number",
        "title",
        "description",
        "category",
        "priority",
        "status",
        "requester_id",
        "assigned_to",
        "source_conversation_id",
        "source_agent_run_id",
        "diagnosis_summary",
        "idempotency_key",
        "created_at",
        "updated_at",
    },
    "ticket_comments": {
        "id",
        "ticket_id",
        "author_id",
        "body",
        "idempotency_key",
        "created_at",
    },
    "pending_confirmations": {
        "id",
        "actor_id",
        "actor_role",
        "action",
        "risk_level",
        "status",
        "parameters",
        "parameters_summary",
        "impact_summary",
        "idempotency_key",
        "request_fingerprint",
        "source_agent_run_id",
        "source_conversation_id",
        "result",
        "error_code",
        "created_at",
        "confirmed_at",
        "executed_at",
        "cancelled_at",
    },
    "audit_events": {
        "id",
        "actor",
        "action",
        "target",
        "parameters_summary",
        "policy_decision",
        "execution_result",
        "request_id",
        "created_at",
    },
    "agent_runs": {
        "id",
        "request_id",
        "conversation_id",
        "status",
        "intent",
        "intent_confidence",
        "risk_level",
        "current_node",
        "state",
        "error_code",
        "started_at",
        "completed_at",
    },
    "agent_steps": {
        "id",
        "run_id",
        "sequence_number",
        "node_name",
        "status",
        "state_snapshot",
        "error_code",
        "error_message",
        "latency_ms",
        "started_at",
        "completed_at",
    },
    "conversations": {"id", "user_role", "created_at", "updated_at"},
    "messages": {
        "id",
        "conversation_id",
        "sequence_number",
        "role",
        "content",
        "retrieval_query",
        "retrieved_chunk_ids",
        "model_provider",
        "configured_model",
        "model_name",
        "model_attempts",
        "prompt_version",
        "response",
        "status",
        "error_stage",
        "error_code",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_tokens",
        "reasoning_tokens",
        "request_id",
        "created_at",
    },
    "knowledge_sources": {"id", "name", "description", "created_at", "updated_at"},
    "documents": {
        "id",
        "knowledge_source_id",
        "title",
        "source_type",
        "status",
        "visibility",
        "allowed_roles",
        "owner",
        "created_at",
        "updated_at",
    },
    "document_versions": {
        "id",
        "document_id",
        "version",
        "content_hash",
        "effective_at",
        "expires_at",
        "raw_file_path",
        "created_at",
    },
    "document_chunks": {
        "id",
        "document_version_id",
        "chunk_index",
        "content",
        "token_count",
        "section_title",
        "metadata",
        "embedding",
        "embedding_model",
        "embedding_version",
        "indexed_at",
        "created_at",
    },
}


@pytest.mark.integration
async def test_knowledge_migration_creates_required_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    engine = create_async_engine(settings.active_database_url)

    try:
        async with engine.connect() as connection:
            table_columns = await connection.run_sync(
                lambda sync_connection: {
                    table_name: {
                        column["name"]
                        for column in inspect(sync_connection).get_columns(table_name)
                    }
                    for table_name in EXPECTED_COLUMNS
                }
            )
            index_names = set(
                (
                    await connection.execute(
                        text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
                    )
                ).scalars()
            )
            role_names = set((await connection.execute(text("SELECT name FROM roles"))).scalars())
            permission_names = set(
                (await connection.execute(text("SELECT name FROM permissions"))).scalars()
            )
            approval_role_permissions = set(
                (
                    await connection.execute(
                        text(
                            "SELECT r.name, p.name FROM role_permissions rp "
                            "JOIN roles r ON r.id = rp.role_id "
                            "JOIN permissions p ON p.id = rp.permission_id "
                            "WHERE p.name IN ('approval:read', 'approval:decide')"
                        )
                    )
                ).tuples()
            )
            confirmation_checks = await connection.run_sync(
                lambda sync_connection: {
                    item["name"]: item["sqltext"]
                    for item in inspect(sync_connection).get_check_constraints(
                        "pending_confirmations"
                    )
                }
            )
    finally:
        await engine.dispose()
        get_settings.cache_clear()

    assert table_columns == EXPECTED_COLUMNS
    assert "ix_document_chunks_fts" in index_names
    assert role_names == {"employee", "helpdesk", "engineer", "admin", "approver"}
    assert permission_names == {
        "finance_admin_group:request",
        "approval:read",
        "approval:decide",
    }
    assert approval_role_permissions == {
        ("approver", "approval:read"),
        ("approver", "approval:decide"),
    }
    assert "cancelled" in confirmation_checks["ck_pending_confirmations_status"]
