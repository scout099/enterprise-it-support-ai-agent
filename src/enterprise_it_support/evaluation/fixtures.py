"""Idempotent fictional knowledge fixtures shared by evaluation CLIs."""

from dataclasses import replace
from pathlib import Path
from uuid import UUID

from apps.dependencies import build_indexing_service, build_knowledge_retriever

from enterprise_it_support.knowledge.chunking import DocumentChunker
from enterprise_it_support.knowledge.parsers import DocumentParserRegistry
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    SearchFilters,
    SearchResult,
    UserContext,
)
from enterprise_it_support.knowledge.service import DocumentIngestionService, LocalDocumentStorage
from enterprise_it_support.platform.config import Settings
from enterprise_it_support.platform.database import DatabaseManager

FIXTURES = Path("data/evaluation/knowledge")
EVALUATION_DOCUMENTS = (
    ("vpn_configuration_sop.md", "Evaluation VPN Configuration SOP", "Demo IT Operations"),
    (
        "outlook_mail_troubleshooting.txt",
        "Evaluation Outlook Mail Troubleshooting SOP",
        "Demo Messaging Team",
    ),
    (
        "account_common_questions_faq.pdf",
        "Evaluation Account Common Questions FAQ",
        "Demo Identity Team",
    ),
    ("vpn_security_notice.txt", "Evaluation VPN Security Notice", "Demo Security Team"),
    (
        "outlook_calendar_training.txt",
        "Evaluation Outlook Calendar Training",
        "Demo Collaboration Team",
    ),
    (
        "account_profile_update.txt",
        "Evaluation Account Profile Update Guide",
        "Demo HR Systems Team",
    ),
)
EVALUATION_SOURCE_NAME = "Retrieval Evaluation Library"


async def seed_evaluation_fixtures(settings: Settings, database: DatabaseManager) -> None:
    """Import and index the six fictional documents without duplicating versions."""
    ingestion = DocumentIngestionService(
        repository=KnowledgeRepository(database.session_factory),
        parser_registry=DocumentParserRegistry(),
        chunker=DocumentChunker(
            chunk_size=settings.knowledge_chunk_size,
            chunk_overlap=settings.knowledge_chunk_overlap,
        ),
        storage=LocalDocumentStorage(settings.knowledge_storage_path),
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )
    indexing = build_indexing_service(settings, database.session_factory)
    for filename, title, owner in EVALUATION_DOCUMENTS:
        path = FIXTURES / filename
        imported = await ingestion.ingest(
            filename=path.name,
            data=path.read_bytes(),
            title=title,
            owner=owner,
            source_name=EVALUATION_SOURCE_NAME,
        )
        await indexing.index_document(imported.document_id)


class EvaluationCorpusRetriever:
    """Keep offline runs on the versioned fictional corpus, independent of developer data."""

    def __init__(self, wrapped: KnowledgeRetriever, allowed_document_ids: frozenset[UUID]) -> None:
        if not allowed_document_ids:
            raise ValueError("Evaluation corpus must contain at least one Document")
        self._wrapped = wrapped
        self._allowed_document_ids = allowed_document_ids

    async def search(
        self,
        query: str,
        top_k: int,
        filters: SearchFilters,
        user_context: UserContext,
    ) -> tuple[SearchResult, ...]:
        restricted_filters = replace(
            filters,
            document_id=None,
            document_ids=self._allowed_document_ids,
        )
        return await self._wrapped.search(
            query,
            top_k,
            restricted_filters,
            user_context,
        )


def build_evaluation_retriever(
    settings: Settings,
    database: DatabaseManager,
    allowed_document_ids: frozenset[UUID],
) -> EvaluationCorpusRetriever:
    """Wrap the production hybrid retriever with the dataset's fixed corpus boundary."""
    return EvaluationCorpusRetriever(
        build_knowledge_retriever(settings, database.session_factory),
        allowed_document_ids,
    )
