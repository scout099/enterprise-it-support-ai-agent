"""FastAPI routes for Phase 3 Chunk embedding indexing."""

from uuid import UUID

from fastapi import APIRouter, Request

from enterprise_it_support.interaction.errors import ApplicationError, ServiceUnavailableError
from enterprise_it_support.knowledge.index_schemas import (
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexStatusResponse,
)
from enterprise_it_support.knowledge.indexing import (
    IndexingDocumentNotFoundError,
    IndexingService,
)

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge-indexing"])


def _service(request: Request) -> IndexingService:
    service = request.app.state.indexing_service
    if service is None:
        raise ServiceUnavailableError("Knowledge indexing service is not configured")
    return service


@router.post("/{document_id}/index", response_model=IndexDocumentResponse)
async def index_document(
    document_id: UUID,
    request: Request,
    options: IndexDocumentRequest | None = None,
) -> IndexDocumentResponse:
    """Index pending Chunks or force a full Document reindex."""
    try:
        result = await _service(request).index_document(
            document_id,
            force=options.force if options else False,
        )
    except IndexingDocumentNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="knowledge_document_not_found",
            message=str(exception),
        ) from exception
    return IndexDocumentResponse(**result.__dict__)


@router.get("/{document_id}/index-status", response_model=IndexStatusResponse)
async def get_index_status(document_id: UUID, request: Request) -> IndexStatusResponse:
    """Return current configured Profile coverage for one Document."""
    try:
        status = await _service(request).get_status(document_id)
    except IndexingDocumentNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="knowledge_document_not_found",
            message=str(exception),
        ) from exception
    return IndexStatusResponse(**status.__dict__)
