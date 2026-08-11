"""Shared HTTP response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Process liveness response."""

    status: str
    service: str
    version: str


class ReadyResponse(BaseModel):
    """Dependency readiness response."""

    status: str
    checks: dict[str, str]


class ErrorDetail(BaseModel):
    """Stable error details returned by every HTTP error handler."""

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Unified error envelope."""

    error: ErrorDetail
