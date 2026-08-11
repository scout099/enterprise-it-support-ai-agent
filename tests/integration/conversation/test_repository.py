"""Conversation repository tests against PostgreSQL."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from enterprise_it_support.conversation.repository import (
    ConversationRepository,
    ConversationRoleMismatchError,
)
from enterprise_it_support.intelligence.model_gateway import TokenUsage
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


@pytest.fixture
async def conversation_repository(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST)
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory.begin() as session:
        await session.execute(text("TRUNCATE messages, conversations CASCADE"))
    try:
        yield ConversationRepository(database.session_factory)
    finally:
        await database.close()
        get_settings.cache_clear()


@pytest.mark.integration
async def test_repository_saves_multiple_turns_with_complete_trace(
    conversation_repository: ConversationRepository,
) -> None:
    first_chunk = uuid4()
    first = await conversation_repository.save_turn(
        conversation_id=None,
        user_role="employee",
        question="How do I configure VPN?",
        retrieval_query="How do I configure VPN?",
        retrieved_chunk_ids=(first_chunk,),
        model_provider="fake",
        configured_model="fake-chat-v1",
        model_name="fake-chat-v1",
        model_attempts=1,
        prompt_version="rag-answer-v1",
        response={"answer": "Use the documented VPN profile."},
        latency_ms=25,
        token_usage=TokenUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cached_tokens=2,
            reasoning_tokens=1,
        ),
        request_id="turn-one",
    )
    second = await conversation_repository.save_turn(
        conversation_id=first.conversation_id,
        user_role="employee",
        question="What if it times out?",
        retrieval_query="What if it times out?",
        retrieved_chunk_ids=(),
        model_provider="not_called",
        configured_model="fake-chat-v1",
        model_name="not-called",
        model_attempts=0,
        prompt_version="rag-answer-v1",
        response={"answer": "The knowledge base does not contain enough evidence."},
        latency_ms=3,
        token_usage=TokenUsage(),
        request_id="turn-two",
    )

    stored = await conversation_repository.get(first.conversation_id)

    assert second.conversation_id == first.conversation_id
    assert [message.sequence_number for message in stored.messages] == [1, 2, 3, 4]
    assert [message.role for message in stored.messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert stored.messages[1].retrieved_chunk_ids == (first_chunk,)
    assert stored.messages[1].model_name == "fake-chat-v1"
    assert stored.messages[1].model_provider == "fake"
    assert stored.messages[1].configured_model == "fake-chat-v1"
    assert stored.messages[1].model_attempts == 1
    assert stored.messages[1].prompt_version == "rag-answer-v1"
    assert stored.messages[1].latency_ms == 25
    assert stored.messages[1].token_usage.total_tokens == 15
    assert stored.messages[1].token_usage.cached_tokens == 2
    assert stored.messages[1].token_usage.reasoning_tokens == 1
    assert stored.messages[3].request_id == "turn-two"


@pytest.mark.integration
async def test_repository_rejects_role_change_on_existing_conversation(
    conversation_repository: ConversationRepository,
) -> None:
    first = await conversation_repository.save_turn(
        conversation_id=None,
        user_role="employee",
        question="Account question",
        retrieval_query="Account question",
        retrieved_chunk_ids=(),
        model_provider="not_called",
        configured_model="fake-chat-v1",
        model_name="not-called",
        model_attempts=0,
        prompt_version="rag-answer-v1",
        response={"answer": "Insufficient evidence."},
        latency_ms=1,
        token_usage=TokenUsage(),
        request_id="role-one",
    )

    with pytest.raises(ConversationRoleMismatchError):
        await conversation_repository.save_turn(
            conversation_id=first.conversation_id,
            user_role="helpdesk",
            question="Continue as another role",
            retrieval_query="Continue as another role",
            retrieved_chunk_ids=(),
            model_provider="not_called",
            configured_model="fake-chat-v1",
            model_name="not-called",
            model_attempts=0,
            prompt_version="rag-answer-v1",
            response={"answer": "Must not save."},
            latency_ms=1,
            token_usage=TokenUsage(),
            request_id="role-two",
        )
