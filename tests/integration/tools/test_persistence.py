"""PostgreSQL audit coverage for successful and rejected tool calls."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from enterprise_it_support.agent_runtime.models import AgentRun
from enterprise_it_support.agent_runtime.persistence import AgentRunRepository
from enterprise_it_support.agent_runtime.state import initial_agent_state
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager
from enterprise_it_support.tools.contracts import (
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionStatus,
)
from enterprise_it_support.tools.gateway import RolePermissionPolicy, ToolExecutionGateway
from enterprise_it_support.tools.mock import (
    create_mock_tool_registry,
    default_tool_permissions,
)
from enterprise_it_support.tools.models import ToolExecution
from enterprise_it_support.tools.persistence import ToolExecutionRepository


@pytest.fixture
async def tool_database(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DatabaseManager, AgentRunRepository, ToolExecutionRepository]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory() as session, session.begin():
        await session.execute(delete(ToolExecution))
        await session.execute(delete(AgentRun))
    try:
        yield (
            database,
            AgentRunRepository(database.session_factory),
            ToolExecutionRepository(database.session_factory),
        )
    finally:
        await database.close()
        get_settings.cache_clear()


@pytest.mark.integration
async def test_gateway_persists_success_invalid_input_and_permission_denial(
    tool_database: tuple[DatabaseManager, AgentRunRepository, ToolExecutionRepository],
) -> None:
    _, run_repository, tool_repository = tool_database
    run_id = uuid4()
    state = initial_agent_state(
        run_id=str(run_id),
        request_id="tool-audit-integration",
        conversation_id=None,
        user_message="VPN cannot connect",
        user_role="employee",
    )
    await run_repository.create_run(state)
    gateway = ToolExecutionGateway(
        registry=create_mock_tool_registry(),
        policy=RolePermissionPolicy(default_tool_permissions()),
        execution_store=tool_repository,
    )

    successful = await gateway.execute(
        ToolExecutionRequest(
            tool_name="get_device_info",
            arguments={"device_ref": "current"},
            context=ToolExecutionContext(
                run_id=run_id,
                request_id="tool-audit-integration",
                node_name="vpn_collect_context",
                user_role="employee",
            ),
        )
    )
    invalid = await gateway.execute(
        ToolExecutionRequest(
            tool_name="get_device_info",
            arguments={"unexpected": True},
            context=ToolExecutionContext(
                run_id=run_id,
                request_id="tool-audit-integration",
                node_name="vpn_collect_context",
                user_role="employee",
            ),
        )
    )
    denied = await gateway.execute(
        ToolExecutionRequest(
            tool_name="get_vpn_service_status",
            arguments={},
            context=ToolExecutionContext(
                run_id=run_id,
                request_id="tool-audit-integration",
                node_name="vpn_check_service",
                user_role="guest",
            ),
        )
    )

    stored = await tool_repository.list_for_run(run_id)

    assert successful.status is ToolExecutionStatus.SUCCEEDED
    assert invalid.status is ToolExecutionStatus.INVALID_INPUT
    assert denied.status is ToolExecutionStatus.PERMISSION_DENIED
    assert [item.status for item in stored] == [
        ToolExecutionStatus.SUCCEEDED,
        ToolExecutionStatus.INVALID_INPUT,
        ToolExecutionStatus.PERMISSION_DENIED,
    ]
    assert stored[0].observation is not None
    assert stored[0].observation["os_family"] == "macos"
    assert all(item.has_side_effect is False for item in stored)
    assert stored[1].error_code == "invalid_tool_input"
    assert stored[2].error_code == "tool_permission_denied"
