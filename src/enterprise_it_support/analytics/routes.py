"""FastAPI routes for feedback capture and dashboard analytics."""

from fastapi import APIRouter, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError

from enterprise_it_support.analytics.domain import (
    FeedbackAccessDeniedError,
    FeedbackConflictError,
    FeedbackCreate,
    FeedbackNotFoundError,
)
from enterprise_it_support.analytics.persistence import FeedbackRepository
from enterprise_it_support.analytics.schemas import (
    AnalyticsSummaryResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
)
from enterprise_it_support.analytics.service import AnalyticsService
from enterprise_it_support.interaction.errors import ApplicationError, ServiceUnavailableError
from enterprise_it_support.service_desk.tools import service_desk_permissions

router = APIRouter(tags=["analytics"])


def _feedback_repository(request: Request) -> FeedbackRepository:
    repository: FeedbackRepository | None = request.app.state.feedback_repository
    if repository is None:
        raise ServiceUnavailableError("Feedback service is not configured")
    return repository


def _analytics_service(request: Request) -> AnalyticsService:
    service: AnalyticsService | None = request.app.state.analytics_service
    if service is None:
        raise ServiceUnavailableError("Analytics service is not configured")
    return service


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    payload: FeedbackCreateRequest,
    request: Request,
) -> FeedbackResponse:
    try:
        stored = await _feedback_repository(request).create(
            FeedbackCreate(
                agent_run_id=payload.agent_run_id,
                actor_id=payload.actor_id,
                user_role=payload.user_role,
                resolved=payload.resolved,
                satisfaction_rating=payload.satisfaction_rating,
                comment=payload.comment,
                ticket_number=payload.ticket_number,
                idempotency_key=payload.idempotency_key,
            )
        )
    except FeedbackNotFoundError as exception:
        raise ApplicationError(
            status_code=404,
            code="feedback_target_not_found",
            message="Feedback target was not found",
        ) from exception
    except FeedbackAccessDeniedError as exception:
        raise ApplicationError(
            status_code=403,
            code="feedback_access_denied",
            message="Feedback target cannot be accessed by this actor",
        ) from exception
    except FeedbackConflictError as exception:
        raise ApplicationError(
            status_code=409,
            code="feedback_conflict",
            message="Feedback was already submitted with different values",
        ) from exception
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError("Feedback could not be saved") from exception
    return FeedbackResponse.model_validate(stored, from_attributes=True)


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    request: Request,
    actor_id: str = Query(min_length=1, max_length=128),
    user_role: str = Query(min_length=1, max_length=100),
    days: int = Query(default=30, ge=1, le=365),
    evaluation_limit: int = Query(default=5, ge=1, le=20),
) -> AnalyticsSummaryResponse:
    _ = actor_id
    permissions = service_desk_permissions().get(user_role.strip(), frozenset())
    if "audit:read" not in permissions:
        raise ApplicationError(
            status_code=403,
            code="analytics_access_denied",
            message="Analytics requires local support authority",
        )
    try:
        return await _analytics_service(request).summary(
            days=days,
            evaluation_limit=evaluation_limit,
        )
    except SQLAlchemyError as exception:
        raise ServiceUnavailableError("Analytics are temporarily unavailable") from exception
