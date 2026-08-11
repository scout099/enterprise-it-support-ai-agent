"""Conversation repository tests against PostgreSQL."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from enterprise_it_support.conversation.repository import (
    ConversationRepository,
    ConversationRoleMismatchError,
    ErrorStage,
    TurnStatus,
    TurnTrace,
)
from enterprise_it_support.intelligence.model_gateway import ModelCallMetadata, TokenUsage
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


def turn_trace(
    *,
    question: str,
    request_id: str,
    response: dict[str, str] | None,
    status: TurnStatus,
    chunk_ids=(),
    error_stage: ErrorStage | None = None,
    error_code: str | None = None,
) -> TurnTrace:
    model_called = status is TurnStatus.SUCCEEDED
    metadata = ModelCallMetadata(
        provider="fake" if model_called else "not_called",
        configured_model="fake-chat-v1",
        resolved_model="fake-chat-v1" if model_called else "not-called",
        prompt_version="rag-answer-v1",
        attempts=1 if model_called else 0,
        usage=(
            TokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                cached_tokens=2,
                reasoning_tokens=1,
            )
            if model_called
            else TokenUsage()
        ),
    )
    return TurnTrace(
        question=question,
        retrieval_query=question,
        retrieved_chunk_ids=tuple(chunk_ids),
        model_metadata=metadata,
        assistant_content=(
            response["answer"] if response is not None else "No grounded answer was produced."
        ),
        response=response,
        latency_ms=25,
        request_id=request_id,
        status=status,
        error_stage=error_stage,
        error_code=error_code,
    )


@pytest.mark.integration
async def test_repository_saves_multiple_turns_with_complete_trace(
    conversation_repository: ConversationRepository,
) -> None:
    first_chunk = uuid4()
    first = await conversation_repository.save_turn(
        conversation_id=None,
        user_role="employee",
        trace=turn_trace(
            question="How do I configure VPN?",
            request_id="turn-one",
            response={"answer": "Use the documented VPN profile."},
            status=TurnStatus.SUCCEEDED,
            chunk_ids=(first_chunk,),
        ),
    )
    second = await conversation_repository.save_turn(
        conversation_id=first.conversation_id,
        user_role="employee",
        trace=turn_trace(
            question="What if it times out?",
            request_id="turn-two",
            response={"answer": "The knowledge base does not contain enough evidence."},
            status=TurnStatus.REFUSED,
        ),
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
    assert stored.messages[1].status is TurnStatus.SUCCEEDED
    assert stored.messages[3].status is TurnStatus.REFUSED
    assert stored.messages[3].request_id == "turn-two"


@pytest.mark.integration
async def test_repository_rejects_role_change_on_existing_conversation(
    conversation_repository: ConversationRepository,
) -> None:
    first = await conversation_repository.save_turn(
        conversation_id=None,
        user_role="employee",
        trace=turn_trace(
            question="Account question",
            request_id="role-one",
            response={"answer": "Insufficient evidence."},
            status=TurnStatus.REFUSED,
        ),
    )

    with pytest.raises(ConversationRoleMismatchError):
        await conversation_repository.save_turn(
            conversation_id=first.conversation_id,
            user_role="helpdesk",
            trace=turn_trace(
                question="Continue as another role",
                request_id="role-two",
                response={"answer": "Must not save."},
                status=TurnStatus.REFUSED,
            ),
        )


@pytest.mark.integration
async def test_repository_persists_failed_turn_without_response_or_sensitive_error(
    conversation_repository: ConversationRepository,
) -> None:
    saved = await conversation_repository.save_turn(
        conversation_id=None,
        user_role="employee",
        trace=turn_trace(
            question="VPN failure",
            request_id="failed-turn",
            response=None,
            status=TurnStatus.FAILED,
            error_stage=ErrorStage.MODEL,
            error_code="model_timeout",
        ),
    )

    stored = await conversation_repository.get(saved.conversation_id)
    assistant = stored.messages[1]

    assert assistant.status is TurnStatus.FAILED
    assert assistant.error_stage is ErrorStage.MODEL
    assert assistant.error_code == "model_timeout"
    assert assistant.response is None
    assert "sensitive" not in assistant.content
