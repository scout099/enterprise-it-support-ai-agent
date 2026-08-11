"""Unified HTTP error handling."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from enterprise_it_support.interaction.schemas import ErrorDetail, ErrorResponse
from enterprise_it_support.platform.logging import reset_request_id, set_request_id

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Base error carrying a stable public HTTP representation."""

    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ServiceUnavailableError(ApplicationError):
    """Raised when a required application dependency is unavailable."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=503,
            code="service_unavailable",
            message=message,
        )


class BadGatewayError(ApplicationError):
    """Raised when an upstream dependency returns an unusable response."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=502,
            code="bad_gateway",
            message=message,
        )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = _request_id(request)
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, request_id=request_id))
    response = JSONResponse(status_code=status_code, content=body.model_dump())
    response.headers["X-Request-ID"] = request_id
    return response


async def http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    """Map framework HTTP errors to the application error envelope."""
    if exception.status_code == 404:
        return _error_response(
            request,
            status_code=404,
            code="not_found",
            message="Resource not found",
        )
    return _error_response(
        request,
        status_code=exception.status_code,
        code="http_error",
        message=str(exception.detail),
    )


async def application_exception_handler(
    request: Request,
    exception: ApplicationError,
) -> JSONResponse:
    """Render deliberate application failures with their stable error code."""
    return _error_response(
        request,
        status_code=exception.status_code,
        code=exception.code,
        message=exception.message,
    )


async def validation_exception_handler(
    request: Request,
    _exception: RequestValidationError,
) -> JSONResponse:
    """Return stable validation errors without exposing internal details."""
    return _error_response(
        request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
    )


async def unhandled_exception_handler(request: Request, exception: Exception) -> JSONResponse:
    """Return a safe response for unexpected errors."""
    token = set_request_id(_request_id(request))
    try:
        logger.error("unhandled_application_error error_type=%s", type(exception).__name__)
    finally:
        reset_request_id(token)
    return _error_response(
        request,
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install all application exception handlers."""
    app.add_exception_handler(ApplicationError, application_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
