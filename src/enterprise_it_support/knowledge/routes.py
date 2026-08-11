"""FastAPI routes for Phase 2 knowledge document ingestion and reads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, Response, UploadFile

from enterprise_it_support.interaction.errors import ApplicationError, ServiceUnavailableError
from enterprise_it_support.knowledge.parsers import (
    DocumentParseError,
    UnsupportedDocumentTypeError,
)
from enterprise_it_support.knowledge.repository import DocumentSourceTypeConflictError
from enterprise_it_support.knowledge.schemas import (
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentImportResponse,
    DocumentSummaryResponse,
    DocumentVersionResponse,
)
from enterprise_it_support.knowledge.service import (
    DocumentIngestionError,
    DocumentIngestionService,
    DocumentNotFoundError,
    DocumentTooLargeError,
    EmptyDocumentError,
)

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])


def _service(request: Request) -> DocumentIngestionService:
    service = request.app.state.knowledge_service
    if service is None:
        raise ServiceUnavailableError("Knowledge service is not configured")
    return service


@router.post("", response_model=DocumentImportResponse, status_code=201)
async def upload_document(
    request: Request,
    response: Response,
    file: Annotated[UploadFile, File()],
    owner: Annotated[str, Form(min_length=1, max_length=200)],
    source_name: Annotated[str, Form(min_length=1, max_length=200)],
    title: Annotated[str | None, Form(max_length=500)] = None,
    source_description: Annotated[str | None, Form(max_length=2000)] = None,
) -> DocumentImportResponse:
    """Upload, parse, chunk, deduplicate, and persist one knowledge document."""
    if not file.filename:
        raise ApplicationError(
            status_code=422,
            code="invalid_filename",
            message="Filename is required",
        )
    maximum_size = request.app.state.settings.knowledge_max_file_size_bytes
    data = await file.read(maximum_size + 1)
    try:
        result = await _service(request).ingest(
            filename=file.filename,
            data=data,
            title=title,
            owner=owner,
            source_name=source_name,
            source_description=source_description,
        )
    except DocumentTooLargeError as exception:
        raise ApplicationError(
            status_code=413,
            code="document_too_large",
            message=str(exception),
        ) from exception
    except UnsupportedDocumentTypeError as exception:
        raise ApplicationError(
            status_code=415,
            code="unsupported_document_type",
            message=str(exception),
        ) from exception
    except DocumentSourceTypeConflictError as exception:
        raise ApplicationError(
            status_code=409,
            code="document_source_type_conflict",
            message=str(exception),
        ) from exception
    except (DocumentParseError, EmptyDocumentError, DocumentIngestionError) as exception:
        raise ApplicationError(
            status_code=422,
            code="document_ingestion_failed",
            message=str(exception),
        ) from exception

    if not result.created_version:
        response.status_code = 200
    return DocumentImportResponse(**result.__dict__)


@router.get("", response_model=list[DocumentSummaryResponse])
async def list_documents(request: Request) -> list[DocumentSummaryResponse]:
    """List logical knowledge documents and their latest version."""
    documents = await _service(request).list_documents()
    return [DocumentSummaryResponse(**document.__dict__) for document in documents]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: UUID, request: Request) -> DocumentDetailResponse:
    """Return one logical document and all retained versions."""
    try:
        document = await _service(request).get_document(document_id)
    except DocumentNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="knowledge_document_not_found",
            message=str(exception),
        ) from exception
    return DocumentDetailResponse(
        id=document.id,
        knowledge_source_id=document.knowledge_source_id,
        source_name=document.source_name,
        title=document.title,
        source_type=document.source_type,
        status=document.status,
        owner=document.owner,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[
            DocumentVersionResponse(
                id=version.id,
                version=version.version,
                content_hash=version.content_hash,
                effective_at=version.effective_at,
                expires_at=version.expires_at,
                created_at=version.created_at,
            )
            for version in document.versions
        ],
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(document_id: UUID, request: Request) -> DocumentChunksResponse:
    """Return ordered chunks from a document's latest version."""
    try:
        result = await _service(request).get_latest_chunks(document_id)
    except DocumentNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="knowledge_document_not_found",
            message=str(exception),
        ) from exception
    return DocumentChunksResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        version=result.version,
        chunks=[chunk.__dict__ for chunk in result.chunks],
    )
