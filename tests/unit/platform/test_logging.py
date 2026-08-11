"""Structured logging behavior tests."""

import json
import logging
from io import StringIO

import pytest

from enterprise_it_support.platform.logging import (
    JsonFormatter,
    configure_logging,
    reset_request_id,
    set_request_id,
)


def test_json_log_contains_required_fields_and_request_id() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("enterprise_it_support.test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    token = set_request_id("req-123")

    try:
        logger.info("health_check_completed")
    finally:
        reset_request_id(token)
        logger.handlers = []

    payload = json.loads(stream.getvalue())
    assert set(payload) == {"timestamp", "level", "module", "message", "request_id"}
    assert payload["level"] == "INFO"
    assert payload["module"] == "enterprise_it_support.test"
    assert payload["message"] == "health_check_completed"
    assert payload["request_id"] == "req-123"
    assert payload["timestamp"].endswith("Z")


def test_json_log_redacts_sensitive_values() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="enterprise_it_support.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="authentication_failed api_key=super-secret password=hunter2",
        args=(),
        exc_info=None,
    )

    rendered = formatter.format(record)

    assert "super-secret" not in rendered
    assert "hunter2" not in rendered
    assert rendered.count("[REDACTED]") == 2


def test_json_log_redacts_bearer_json_and_database_url_credentials() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="enterprise_it_support.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=(
            "request_failed Authorization: Bearer bearer-secret "
            'payload={"api_key": "json-secret"} '
            "database_url=postgresql+psycopg://user:database-secret@localhost/app"
        ),
        args=(),
        exc_info=None,
    )

    rendered = formatter.format(record)

    assert "bearer-secret" not in rendered
    assert "json-secret" not in rendered
    assert "database-secret" not in rendered
    assert rendered.count("[REDACTED]") == 3


def test_configure_logging_routes_uvicorn_logs_to_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    uvicorn_logger = logging.getLogger("uvicorn.error")
    previous_handlers = uvicorn_logger.handlers[:]
    previous_propagate = uvicorn_logger.propagate
    legacy_stream = StringIO()
    uvicorn_logger.handlers = [logging.StreamHandler(legacy_stream)]
    uvicorn_logger.propagate = False

    try:
        configure_logging("INFO")
        uvicorn_logger.info("server_started")
        payload = json.loads(capsys.readouterr().out)
    finally:
        uvicorn_logger.handlers = previous_handlers
        uvicorn_logger.propagate = previous_propagate

    assert payload["level"] == "INFO"
    assert payload["module"] == "uvicorn.error"
    assert payload["message"] == "server_started"
    assert legacy_stream.getvalue() == ""


def test_configure_logging_keeps_disabled_uvicorn_access_log_disabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    access_logger = logging.getLogger("uvicorn.access")
    previous_handlers = access_logger.handlers[:]
    previous_propagate = access_logger.propagate
    access_logger.handlers = []
    access_logger.propagate = False

    try:
        configure_logging("INFO")
        access_logger.info("request_completed")
        output = capsys.readouterr().out
    finally:
        access_logger.handlers = previous_handlers
        access_logger.propagate = previous_propagate

    assert output == ""
