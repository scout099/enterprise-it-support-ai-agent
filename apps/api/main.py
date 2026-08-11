"""FastAPI composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.dependencies import (
    build_indexing_service,
    build_knowledge_retriever,
    build_model_gateway,
    build_relevance_policy,
)
from enterprise_it_support.agent_runtime.rag import RAGAnswerService
from enterprise_it_support.conversation.repository import ConversationRepository
from enterprise_it_support.conversation.routes import router as chat_router
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


def create_app(
    settings: Settings | None = None,
    database_manager: DatabaseLifecycle | None = None,
    knowledge_service: DocumentIngestionService | None = None,
    indexing_service: IndexingService | None = None,
    knowledge_retriever: KnowledgeRetriever | None = None,
    model_gateway: ModelGateway | None = None,
    conversation_repository: ConversationRepository | None = None,
    rag_answer_service: RAGAnswerService | None = None,
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
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
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
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(router)
    app.include_router(knowledge_router)
    app.include_router(index_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    return app
