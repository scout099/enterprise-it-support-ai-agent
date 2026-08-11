"""Structured JSON logging with request correlation and basic redaction."""

import json
import logging
import re
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_url_credentials = re.compile(r"(?i)(?P<prefix>\b[a-z][a-z0-9+.-]*://[^:\s/@]+:)[^@\s]+(?=@)")
_authorization_credentials = re.compile(
    r"""(?ix)
    (?P<prefix>\bauthorization\b["']?\s*[:=]\s*)
    ["']?(?:bearer|basic)\s+[^"'\s,;}]+["']?
    """
)
_sensitive_value = re.compile(
    r"""(?ix)
    (?P<prefix>["']?\b(?:api[_-]?key|authorization|password|secret|token)\b["']?\s*[:=]\s*)
    ["']?[^"'\s,;}]+["']?
    """
)


def set_request_id(request_id: str) -> Token[str | None]:
    """Bind a request ID to the current async context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request ID after request processing."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request ID bound to the current async context."""
    return _request_id.get()


def _redact(message: str) -> str:
    message = _url_credentials.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        message,
    )
    message = _authorization_credentials.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        message,
    )
    return _sensitive_value.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        message,
    )


class JsonFormatter(logging.Formatter):
    """Render a deliberately small, predictable JSON log schema."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC)
        payload = {
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "module": record.name,
            "message": _redact(record.getMessage()),
            "request_id": get_request_id(),
        }
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_level: str) -> None:
    """Configure process logging without serializing arbitrary record extras."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error"):
        server_logger = logging.getLogger(logger_name)
        server_logger.handlers = []
        server_logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    if access_logger.handlers:
        access_logger.handlers = []
        access_logger.propagate = True
