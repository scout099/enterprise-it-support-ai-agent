"""FastAPI route for Retrieval-only hybrid knowledge search."""

from fastapi import APIRouter, Request

from enterprise_it_support.interaction.errors import ServiceUnavailableError
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    RetrievalUnavailableError,
    SearchFilters,
    UserContext,
)
from enterprise_it_support.knowledge.search_schemas import (
    CitationResponse,
    KnowledgeSearchRequest,
    SearchResultResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge-retrieval"])


def _retriever(request: Request) -> KnowledgeRetriever:
    retriever = request.app.state.knowledge_retriever
    if retriever is None:
        raise ServiceUnavailableError("Knowledge retrieval service is not configured")
    return retriever


@router.post("/search", response_model=list[SearchResultResponse])
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    request: Request,
) -> list[SearchResultResponse]:
    """Return authorized ranked evidence without generating a chat answer."""
    try:
        results = await _retriever(request).search(
            payload.query,
            payload.top_k,
            SearchFilters(**payload.filters.model_dump()),
            UserContext(role=payload.user_role),
        )
    except RetrievalUnavailableError as exception:
        raise ServiceUnavailableError(
            "Knowledge retrieval is temporarily unavailable"
        ) from exception
    return [
        SearchResultResponse(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_title=result.document_title,
            document_version=result.document_version,
            content=result.content,
            section_title=result.section_title,
            score=result.score,
            retrieval_method=result.retrieval_method,
            citation=CitationResponse(**result.citation.__dict__),
        )
        for result in results
    ]
