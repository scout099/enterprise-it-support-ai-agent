"""Phase 1 operational HTTP routes."""

from fastapi import APIRouter, Request

from enterprise_it_support.interaction.errors import ServiceUnavailableError
from enterprise_it_support.interaction.schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["operations"])
async def health(request: Request) -> HealthResponse:
    """Report process liveness without touching external dependencies."""
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadyResponse, tags=["operations"])
async def ready(request: Request) -> ReadyResponse:
    """Report whether required infrastructure can serve application traffic."""
    result = await request.app.state.database_manager.check()
    if not result.ready:
        raise ServiceUnavailableError("Database is not ready")
    return ReadyResponse(status="ready", checks={"database": "ok"})
