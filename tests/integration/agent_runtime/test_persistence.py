"""PostgreSQL Agent Run/Step and LangGraph checkpoint integration tests."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import delete

from enterprise_it_support.agent_runtime.models import AgentRun, AgentStep
from enterprise_it_support.agent_runtime.persistence import AgentRunRepository
from enterprise_it_support.agent_runtime.state import (
    AgentIntent,
    AgentRunStatus,
    AgentState,
    AgentStepStatus,
    initial_agent_state,
)
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager
from enterprise_it_support.tools.models import ToolExecution


@pytest.fixture
async def agent_database(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Settings, DatabaseManager]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory() as session, session.begin():
        await session.execute(delete(ToolExecution))
        await session.execute(delete(AgentStep))
        await session.execute(delete(AgentRun))
    try:
        yield settings, database
    finally:
        await database.close()
        get_settings.cache_clear()


@pytest.mark.integration
async def test_agent_repository_saves_run_and_append_only_steps(
    agent_database: tuple[Settings, DatabaseManager],
) -> None:
    _, database = agent_database
    repository = AgentRunRepository(database.session_factory)
    run_id = uuid4()
    state = initial_agent_state(
        run_id=str(run_id),
        request_id="agent-persistence",
        conversation_id=None,
        user_message="VPN cannot connect",
        user_role="employee",
    )
    await repository.create_run(state)

    state["current_node"] = "intake"
    state["node_count"] = 1
    await repository.save_step(
        state=state,
        node_name="intake",
        status=AgentStepStatus.SUCCEEDED,
        latency_ms=2,
    )
    state["current_node"] = "classify_intent"
    state["node_count"] = 2
    state["intent"] = AgentIntent.VPN_DIAGNOSIS.value
    state["intent_confidence"] = 0.91
    state["status"] = AgentRunStatus.COMPLETED.value
    state["final_response"] = {"summary": "VPN diagnosis placeholder"}
    await repository.save_step(
        state=state,
        node_name="classify_intent",
        status=AgentStepStatus.SUCCEEDED,
        latency_ms=3,
    )

    stored = await repository.get(run_id)

    assert stored.status is AgentRunStatus.COMPLETED
    assert stored.intent == AgentIntent.VPN_DIAGNOSIS.value
    assert stored.intent_confidence == 0.91
    assert [step.sequence_number for step in stored.steps] == [1, 2]
    assert [step.node_name for step in stored.steps] == ["intake", "classify_intent"]
    assert all(step.status is AgentStepStatus.SUCCEEDED for step in stored.steps)
    assert stored.state["final_response"]["summary"] == "VPN diagnosis placeholder"


@pytest.mark.integration
async def test_agent_repository_clears_completion_time_when_run_resumes(
    agent_database: tuple[Settings, DatabaseManager],
) -> None:
    _, database = agent_database
    repository = AgentRunRepository(database.session_factory)
    run_id = uuid4()
    state = initial_agent_state(
        run_id=str(run_id),
        request_id="agent-resume-lifecycle",
        conversation_id=None,
        user_message="Resume this Agent",
        user_role="employee",
    )
    await repository.create_run(state)
    state["status"] = AgentRunStatus.FAILED.value
    state["error"] = {"code": "agent_timeout", "message": "Safe timeout"}
    await repository.update_run(state)
    assert (await repository.get(run_id)).completed_at is not None

    state["status"] = AgentRunStatus.RUNNING.value
    state["error"] = None
    await repository.update_run(state)

    resumed = await repository.get(run_id)
    assert resumed.status is AgentRunStatus.RUNNING
    assert resumed.completed_at is None


@pytest.mark.integration
async def test_postgres_checkpoint_restores_state_across_saver_instances(
    agent_database: tuple[Settings, DatabaseManager],
) -> None:
    settings, _ = agent_database
    checkpoint_url = settings.active_database_url.replace("postgresql+psycopg://", "postgresql://")
    thread_id = str(uuid4())

    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as saver:
        await saver.setup()
        builder = StateGraph(AgentState)

        async def mark_intent(_state: AgentState) -> dict[str, object]:
            return {
                "intent": AgentIntent.ACCOUNT_DIAGNOSIS.value,
                "intent_confidence": 0.88,
                "current_node": "classify_intent",
            }

        builder.add_node("classify_intent", mark_intent)
        builder.add_edge(START, "classify_intent")
        builder.add_edge("classify_intent", END)
        graph = builder.compile(checkpointer=saver)
        initial = initial_agent_state(
            run_id=thread_id,
            request_id="postgres-checkpoint",
            conversation_id=None,
            user_message="My account is locked",
            user_role="employee",
        )
        await graph.ainvoke(
            initial,
            config={"configurable": {"thread_id": thread_id}},
        )

    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as restored_saver:
        restored_builder = StateGraph(AgentState)
        restored_builder.add_node("classify_intent", mark_intent)
        restored_builder.add_edge(START, "classify_intent")
        restored_builder.add_edge("classify_intent", END)
        restored_graph = restored_builder.compile(checkpointer=restored_saver)
        snapshot = await restored_graph.aget_state({"configurable": {"thread_id": thread_id}})

    assert snapshot.values["request_id"] == "postgres-checkpoint"
    assert snapshot.values["intent"] == AgentIntent.ACCOUNT_DIAGNOSIS.value
    assert snapshot.values["intent_confidence"] == 0.88
