"""Public readiness endpoint tests."""

from apps.api.main import create_app
from fastapi.testclient import TestClient

from enterprise_it_support.platform.config import Settings
from enterprise_it_support.platform.database import DatabaseCheckResult


class ReadyDatabaseAdapter:
    """Database boundary adapter for HTTP behavior tests."""

    async def check(self) -> DatabaseCheckResult:
        return DatabaseCheckResult(ready=True, reason="ok")

    async def close(self) -> None:
        return None


class UnavailableDatabaseAdapter:
    """Database boundary adapter representing a failed dependency."""

    async def check(self) -> DatabaseCheckResult:
        return DatabaseCheckResult(ready=False, reason="connection_failed")

    async def close(self) -> None:
        return None


def test_ready_endpoint_reports_database_status(test_settings: Settings) -> None:
    app = create_app(settings=test_settings, database_manager=ReadyDatabaseAdapter())

    with TestClient(app) as client:
        response = client.get("/ready", headers={"X-Request-ID": "ready-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
    assert response.headers["x-request-id"] == "ready-123"


def test_ready_endpoint_returns_unified_error_when_database_is_unavailable(
    test_settings: Settings,
) -> None:
    app = create_app(settings=test_settings, database_manager=UnavailableDatabaseAdapter())

    with TestClient(app) as client:
        response = client.get("/ready", headers={"X-Request-ID": "ready-503"})

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "Database is not ready",
            "request_id": "ready-503",
        }
    }
