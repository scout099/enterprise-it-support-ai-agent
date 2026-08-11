"""Public health and error response tests."""

import json

import pytest
from apps.api.main import create_app
from fastapi import Query
from fastapi.testclient import TestClient

from enterprise_it_support.platform.config import Settings


def test_health_endpoint_reports_process_status(test_settings: Settings) -> None:
    with TestClient(create_app(settings=test_settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Enterprise IT Support AI Agent",
        "version": "0.1.0",
    }
    assert response.headers["x-request-id"]


def test_request_id_is_preserved_in_response(test_settings: Settings) -> None:
    with TestClient(create_app(settings=test_settings)) as client:
        response = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert response.headers["x-request-id"] == "request-123"


def test_http_errors_use_unified_response_and_request_id(test_settings: Settings) -> None:
    with TestClient(create_app(settings=test_settings)) as client:
        response = client.get("/does-not-exist", headers={"X-Request-ID": "request-404"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Resource not found",
            "request_id": "request-404",
        }
    }
    assert response.headers["x-request-id"] == "request-404"


def test_unhandled_errors_keep_request_id_in_response_and_log(
    test_settings: Settings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = test_settings.model_copy(update={"log_level": "ERROR"})
    app = create_app(settings=settings)

    @app.get("/test/unhandled-error")
    async def raise_unhandled_error() -> None:
        raise RuntimeError("deliberate test failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/test/unhandled-error",
            headers={"X-Request-ID": "request-500"},
        )

    log_records = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred",
            "request_id": "request-500",
        }
    }
    assert response.headers["x-request-id"] == "request-500"
    assert any(
        record["message"].startswith("unhandled_application_error")
        and record["request_id"] == "request-500"
        for record in log_records
    )


def test_validation_errors_use_unified_response(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)

    @app.get("/test/validated-input")
    async def validated_input(limit: int = Query(gt=0)) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(app) as client:
        response = client.get(
            "/test/validated-input?limit=invalid",
            headers={"X-Request-ID": "request-422"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "request_id": "request-422",
        }
    }
    assert response.headers["x-request-id"] == "request-422"
