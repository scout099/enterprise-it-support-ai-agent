"""FastAPI routes for grounded chat and conversation trace reads."""

from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.agent_runtime.rag import (
    RAGAnswerService,
    RAGCitationValidationError,
)
from enterprise_it_support.conversation.repository import (
    ConversationNotFoundError,
    ConversationRepository,
    ConversationRoleMismatchError,
)
from enterprise_it_support.conversation.schemas import (
    ChatAskRequest,
    ChatAskResponse,
    ConversationMessageResponse,
    ConversationResponse,
    TokenUsageResponse,
)
from enterprise_it_support.intelligence.model_gateway import (
    ModelGatewayResponseError,
    ModelGatewayTimeoutError,
    ModelGatewayUnavailableError,
)
from enterprise_it_support.interaction.errors import (
    ApplicationError,
    BadGatewayError,
    ServiceUnavailableError,
)
from enterprise_it_support.knowledge.retrieval import RetrievalUnavailableError

router = APIRouter(prefix="/chat", tags=["chat"])


def _rag_service(request: Request) -> RAGAnswerService:
    service = request.app.state.rag_answer_service
    if service is None:
        raise ServiceUnavailableError("Chat answer service is not configured")
    return service


def _conversation_repository(request: Request) -> ConversationRepository:
    repository = request.app.state.conversation_repository
    if repository is None:
        raise ServiceUnavailableError("Conversation service is not configured")
    return repository


def _not_found() -> ApplicationError:
    return ApplicationError(
        status_code=404,
        code="conversation_not_found",
        message="Conversation was not found",
    )


def _role_mismatch() -> ApplicationError:
    return ApplicationError(
        status_code=403,
        code="conversation_role_mismatch",
        message="Conversation cannot be accessed with this role",
    )


@router.post("/ask", response_model=ChatAskResponse)
async def ask_chat(payload: ChatAskRequest, request: Request) -> ChatAskResponse:
    """Return and persist one grounded enterprise-knowledge answer."""
    try:
        turn = await _rag_service(request).ask(
            question=payload.question,
            user_role=payload.user_role,
            conversation_id=payload.conversation_id,
            request_id=request.state.request_id,
        )
    except ConversationNotFoundError as exception:
        raise _not_found() from exception
    except ConversationRoleMismatchError as exception:
        raise _role_mismatch() from exception
    except (ModelGatewayResponseError, RAGCitationValidationError) as exception:
        raise BadGatewayError("Model returned an invalid grounded response") from exception
    except (
        ModelGatewayTimeoutError,
        ModelGatewayUnavailableError,
        RetrievalUnavailableError,
        SQLAlchemyError,
    ) as exception:
        raise ServiceUnavailableError(
            "Chat answer service is temporarily unavailable"
        ) from exception

    answer = turn.answer
    return ChatAskResponse(
        conversation_id=turn.conversation_id,
        user_message_id=turn.user_message_id,
        assistant_message_id=turn.assistant_message_id,
        summary=answer.summary,
        answer=answer.answer,
        diagnosis=answer.diagnosis,
        citations=answer.citations,
        limitations=answer.limitations,
        next_steps=answer.next_steps,
        confidence=answer.confidence,
        model_name=turn.model_metadata.resolved_model,
        model_provider=turn.model_metadata.provider,
        configured_model=turn.model_metadata.configured_model,
        model_attempts=turn.model_metadata.attempts,
        prompt_version=turn.model_metadata.prompt_version,
        token_usage=TokenUsageResponse(**turn.model_metadata.usage.__dict__),
        latency_ms=turn.latency_ms,
        request_id=turn.request_id,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    user_role: str = Query(min_length=1, max_length=100),
) -> ConversationResponse:
    """Read one complete trace after enforcing its fixed local role."""
    try:
        conversation = await _conversation_repository(request).get(conversation_id)
    except ConversationNotFoundError as exception:
        raise _not_found() from exception
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError(
            "Conversation service is temporarily unavailable"
        ) from exception
    if conversation.user_role != user_role.strip():
        raise _role_mismatch()

    return ConversationResponse(
        id=conversation.id,
        user_role=conversation.user_role,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessageResponse(
                id=message.id,
                sequence_number=message.sequence_number,
                role=message.role,
                content=message.content,
                retrieval_query=message.retrieval_query,
                retrieved_chunk_ids=list(message.retrieved_chunk_ids),
                model_name=message.model_name,
                model_provider=message.model_provider,
                configured_model=message.configured_model,
                model_attempts=message.model_attempts,
                prompt_version=message.prompt_version,
                response=message.response,
                status=message.status,
                error_stage=message.error_stage,
                error_code=message.error_code,
                latency_ms=message.latency_ms,
                token_usage=TokenUsageResponse(**message.token_usage.__dict__),
                request_id=message.request_id,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
    )
