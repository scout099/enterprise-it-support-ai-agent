"""FastAPI composition root."""

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import Error as PsycopgError

from apps.dependencies import (
    build_indexing_service,
    build_knowledge_retriever,
    build_model_gateway,
    build_relevance_policy,
    build_tool_gateway,
)
from enterprise_it_support.agent_runtime.persistence import AgentRunRepository
from enterprise_it_support.agent_runtime.rag import RAGAnswerService
from enterprise_it_support.agent_runtime.routes import router as agent_router
from enterprise_it_support.agent_runtime.runtime import AgentRuntime, AgentRuntimeLimits
from enterprise_it_support.analytics.persistence import AnalyticsRepository, FeedbackRepository
from enterprise_it_support.analytics.routes import router as analytics_router
from enterprise_it_support.analytics.service import AnalyticsService
from enterprise_it_support.conversation.repository import ConversationRepository
from enterprise_it_support.conversation.routes import router as chat_router
from enterprise_it_support.governance.persistence import GovernanceRepository
from enterprise_it_support.governance.policy import PolicyEngine
from enterprise_it_support.governance.routes import router as governance_router
from enterprise_it_support.governance.service import GovernanceService
from enterprise_it_support.intelligence.model_gateway import ModelGateway
from enterprise_it_support.interaction.errors import register_exception_handlers
from enterprise_it_support.interaction.middleware import RequestIDMiddleware
from enterprise_it_support.interaction.routes import router
from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.index_routes import router as index_router
from enterprise_it_support.knowledge.indexing import IndexingService
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.knowledge.retrieval import KnowledgeRetriever
from enterprise_it_support.knowledge.routes import router as knowledge_router
from enterprise_it_support.knowledge.search_routes import router as search_router
from enterprise_it_support.knowledge.service import (
    DocumentIngestionService,
    LocalDocumentStorage,
)
from enterprise_it_support.platform.config import Settings, get_settings
from enterprise_it_support.platform.database import DatabaseLifecycle, DatabaseManager
from enterprise_it_support.platform.logging import configure_logging
from enterprise_it_support.service_desk.persistence import (
    AuditEventRepository,
    PendingConfirmationRepository,
    TicketRepository,
)
from enterprise_it_support.service_desk.routes import router as service_desk_router
from enterprise_it_support.service_desk.service import ServiceDeskService
from enterprise_it_support.tools.gateway import ToolExecutionGateway
from enterprise_it_support.tools.persistence import ToolExecutionRepository

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    database_manager: DatabaseLifecycle | None = None,
    knowledge_service: DocumentIngestionService | None = None,
    indexing_service: IndexingService | None = None,
    knowledge_retriever: KnowledgeRetriever | None = None,
    model_gateway: ModelGateway | None = None,
    conversation_repository: ConversationRepository | None = None,
    rag_answer_service: RAGAnswerService | None = None,
    agent_run_repository: AgentRunRepository | None = None,
    tool_execution_repository: ToolExecutionRepository | None = None,
    tool_gateway: ToolExecutionGateway | None = None,
    ticket_repository: TicketRepository | None = None,
    pending_confirmation_repository: PendingConfirmationRepository | None = None,
    audit_event_repository: AuditEventRepository | None = None,
    service_desk_service: ServiceDeskService | None = None,
    governance_repository: GovernanceRepository | None = None,
    governance_service: GovernanceService | None = None,
    agent_runtime: AgentRuntime | None = None,
    feedback_repository: FeedbackRepository | None = None,
    analytics_service: AnalyticsService | None = None,
) -> FastAPI:
    """Build the application with explicit, testable dependencies."""
    resolved_settings = settings or get_settings()
    resolved_database = database_manager or DatabaseManager(resolved_settings.active_database_url)
    resolved_knowledge_service = knowledge_service
    if resolved_knowledge_service is None and isinstance(resolved_database, DatabaseManager):
        resolved_knowledge_service = DocumentIngestionService(
            repository=KnowledgeRepository(resolved_database.session_factory),
            parser_registry=DocumentParserRegistry(),
            chunker=DocumentChunker(
                chunk_size=resolved_settings.knowledge_chunk_size,
                chunk_overlap=resolved_settings.knowledge_chunk_overlap,
            ),
            storage=LocalDocumentStorage(resolved_settings.knowledge_storage_path),
            max_file_size_bytes=resolved_settings.knowledge_max_file_size_bytes,
        )
    resolved_indexing_service = indexing_service
    if resolved_indexing_service is None and isinstance(resolved_database, DatabaseManager):
        resolved_indexing_service = build_indexing_service(
            resolved_settings,
            resolved_database.session_factory,
        )
    resolved_knowledge_retriever = knowledge_retriever
    if resolved_knowledge_retriever is None and isinstance(resolved_database, DatabaseManager):
        resolved_knowledge_retriever = build_knowledge_retriever(
            resolved_settings,
            resolved_database.session_factory,
        )
    resolved_conversation_repository = conversation_repository
    if resolved_conversation_repository is None and isinstance(resolved_database, DatabaseManager):
        resolved_conversation_repository = ConversationRepository(resolved_database.session_factory)
    resolved_model_gateway = model_gateway or build_model_gateway(resolved_settings)
    resolved_rag_answer_service = rag_answer_service
    if (
        resolved_rag_answer_service is None
        and resolved_knowledge_retriever is not None
        and resolved_conversation_repository is not None
    ):
        resolved_rag_answer_service = RAGAnswerService(
            retriever=resolved_knowledge_retriever,
            model_gateway=resolved_model_gateway,
            conversation_store=resolved_conversation_repository,
            relevance_policy=build_relevance_policy(resolved_settings),
            top_k=resolved_settings.rag_top_k,
            max_context_chars=resolved_settings.rag_max_context_chars,
        )
    resolved_agent_run_repository = agent_run_repository
    if resolved_agent_run_repository is None and isinstance(resolved_database, DatabaseManager):
        resolved_agent_run_repository = AgentRunRepository(resolved_database.session_factory)
    resolved_tool_execution_repository = tool_execution_repository
    if resolved_tool_execution_repository is None and isinstance(
        resolved_database,
        DatabaseManager,
    ):
        resolved_tool_execution_repository = ToolExecutionRepository(
            resolved_database.session_factory
        )
    resolved_ticket_repository = ticket_repository
    if resolved_ticket_repository is None and isinstance(
        resolved_database,
        DatabaseManager,
    ):
        resolved_ticket_repository = TicketRepository(resolved_database.session_factory)
    resolved_pending_confirmation_repository = pending_confirmation_repository
    if resolved_pending_confirmation_repository is None and isinstance(
        resolved_database,
        DatabaseManager,
    ):
        resolved_pending_confirmation_repository = PendingConfirmationRepository(
            resolved_database.session_factory
        )
    resolved_audit_event_repository = audit_event_repository
    if resolved_audit_event_repository is None and isinstance(
        resolved_database,
        DatabaseManager,
    ):
        resolved_audit_event_repository = AuditEventRepository(resolved_database.session_factory)
    resolved_governance_repository = governance_repository
    if resolved_governance_repository is None and isinstance(
        resolved_database,
        DatabaseManager,
    ):
        resolved_governance_repository = GovernanceRepository(resolved_database.session_factory)
    resolved_governance_service = governance_service
    if (
        resolved_governance_service is None
        and resolved_governance_repository is not None
        and resolved_audit_event_repository is not None
    ):
        resolved_governance_service = GovernanceService(
            repository=resolved_governance_repository,
            policy_engine=PolicyEngine(),
            audit_events=resolved_audit_event_repository,
        )
    resolved_feedback_repository = feedback_repository
    resolved_analytics_service = analytics_service
    if isinstance(resolved_database, DatabaseManager):
        if resolved_feedback_repository is None:
            resolved_feedback_repository = FeedbackRepository(resolved_database.session_factory)
        if resolved_analytics_service is None:
            resolved_analytics_service = AnalyticsService(
                AnalyticsRepository(resolved_database.session_factory),
                resolved_settings.evaluation_artifacts_path,
            )
    resolved_tool_gateway = tool_gateway
    if resolved_tool_gateway is None and resolved_tool_execution_repository is not None:
        resolved_tool_gateway = build_tool_gateway(
            resolved_tool_execution_repository,
            ticket_repository=resolved_ticket_repository,
            confirmation_repository=resolved_pending_confirmation_repository,
        )
    resolved_service_desk_service = service_desk_service
    if (
        resolved_service_desk_service is None
        and resolved_tool_gateway is not None
        and resolved_ticket_repository is not None
        and resolved_pending_confirmation_repository is not None
        and resolved_audit_event_repository is not None
    ):
        resolved_service_desk_service = ServiceDeskService(
            gateway=resolved_tool_gateway,
            confirmations=resolved_pending_confirmation_repository,
            tickets=resolved_ticket_repository,
            audit_events=resolved_audit_event_repository,
        )
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(lifespan_app: FastAPI) -> AsyncIterator[None]:
        try:
            if agent_runtime is not None:
                lifespan_app.state.agent_runtime = agent_runtime
                yield
            elif (
                resolved_knowledge_retriever is not None
                and resolved_rag_answer_service is not None
                and resolved_agent_run_repository is not None
                and resolved_tool_gateway is not None
            ):
                checkpoint_url = resolved_settings.active_database_url.replace(
                    "postgresql+psycopg://",
                    "postgresql://",
                )
                checkpoint_stack = AsyncExitStack()
                try:
                    checkpointer = await checkpoint_stack.enter_async_context(
                        AsyncPostgresSaver.from_conn_string(checkpoint_url)
                    )
                    await checkpointer.setup()
                except PsycopgError:
                    await checkpoint_stack.aclose()
                    logger.warning("agent_checkpoint_initialization_failed")
                    lifespan_app.state.agent_runtime = None
                    yield
                else:
                    lifespan_app.state.agent_runtime = AgentRuntime(
                        model_gateway=resolved_model_gateway,
                        retriever=resolved_knowledge_retriever,
                        rag_answer_service=resolved_rag_answer_service,
                        tool_gateway=resolved_tool_gateway,
                        run_store=resolved_agent_run_repository,
                        checkpointer=checkpointer,
                        limits=AgentRuntimeLimits(
                            confidence_threshold=(
                                resolved_settings.agent_intent_confidence_threshold
                            ),
                            max_nodes=resolved_settings.agent_max_nodes,
                            max_retries=resolved_settings.agent_max_retries,
                            max_tool_calls=resolved_settings.agent_max_tool_calls,
                            node_timeout_seconds=(resolved_settings.agent_node_timeout_seconds),
                            total_timeout_seconds=resolved_settings.agent_timeout_seconds,
                        ),
                        top_k=resolved_settings.rag_top_k,
                        governance_service=resolved_governance_service,
                    )
                    try:
                        yield
                    finally:
                        await checkpoint_stack.aclose()
            else:
                yield
        finally:
            await resolved_database.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database_manager = resolved_database
    app.state.knowledge_service = resolved_knowledge_service
    app.state.indexing_service = resolved_indexing_service
    app.state.knowledge_retriever = resolved_knowledge_retriever
    app.state.model_gateway = resolved_model_gateway
    app.state.conversation_repository = resolved_conversation_repository
    app.state.rag_answer_service = resolved_rag_answer_service
    app.state.agent_run_repository = resolved_agent_run_repository
    app.state.tool_execution_repository = resolved_tool_execution_repository
    app.state.tool_gateway = resolved_tool_gateway
    app.state.ticket_repository = resolved_ticket_repository
    app.state.pending_confirmation_repository = resolved_pending_confirmation_repository
    app.state.audit_event_repository = resolved_audit_event_repository
    app.state.service_desk_service = resolved_service_desk_service
    app.state.governance_repository = resolved_governance_repository
    app.state.governance_service = resolved_governance_service
    app.state.agent_runtime = agent_runtime
    app.state.feedback_repository = resolved_feedback_repository
    app.state.analytics_service = resolved_analytics_service
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(router)
    app.include_router(knowledge_router)
    app.include_router(index_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(agent_router)
    app.include_router(service_desk_router)
    app.include_router(governance_router)
    app.include_router(analytics_router)
    return app
