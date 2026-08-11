"""Behavior tests for the UI's HTTP-only FastAPI client."""

from typing import Any

import pytest
import requests
from apps.ui.client import APIError, ITSupportAPIClient


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, ValueError):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse | requests.RequestException]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, requests.RequestException):
            raise response
        return response


def test_client_calls_only_fastapi_contracts_and_keeps_conversation() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"run": {"run_id": "11111111-1111-1111-1111-111111111111"}},
            ),
            FakeResponse(200, {"status": "executed"}),
            FakeResponse(200, {"run_id": "11111111-1111-1111-1111-111111111111"}),
            FakeResponse(200, {"status": "cancelled"}),
            FakeResponse(201, {"resolved": True}),
            FakeResponse(200, {"total_tickets": 2}),
        ]
    )
    client = ITSupportAPIClient("http://api.test/", session=session)  # type: ignore[arg-type]

    client.respond(
        user_message="VPN cannot connect",
        actor_id="employee-1",
        user_role="employee",
        conversation_id="22222222-2222-2222-2222-222222222222",
    )
    client.confirm(confirmation_id="c1", actor_id="employee-1", user_role="employee")
    client.agent_run(
        run_id="11111111-1111-1111-1111-111111111111",
        user_role="employee",
    )
    client.cancel(confirmation_id="c2", actor_id="employee-1", user_role="employee")
    client.submit_feedback(
        agent_run_id="11111111-1111-1111-1111-111111111111",
        actor_id="employee-1",
        user_role="employee",
        resolved=True,
        satisfaction_rating=5,
        comment=None,
        ticket_number=None,
    )
    client.analytics(actor_id="support-1", user_role="it_support", days=30)

    assert [call[1] for call in session.calls] == [
        "http://api.test/agent/respond",
        "http://api.test/agent/confirm",
        "http://api.test/agent/runs/11111111-1111-1111-1111-111111111111",
        "http://api.test/agent/cancel",
        "http://api.test/feedback",
        "http://api.test/analytics/summary",
    ]
    assert session.calls[0][2]["json"]["conversation_id"].startswith("2222")
    assert "timeout" in session.calls[0][2]


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (FakeResponse(403, {"error": {"code": "denied", "message": "Denied"}}), "denied"),
        (FakeResponse(200, ValueError("not json")), "invalid_api_response"),
        (requests.ConnectionError("offline"), "api_unavailable"),
    ],
)
def test_client_returns_safe_errors(
    response: FakeResponse | requests.RequestException,
    expected_code: str,
) -> None:
    client = ITSupportAPIClient(
        "http://api.test",
        session=FakeSession([response]),  # type: ignore[arg-type]
    )

    with pytest.raises(APIError) as raised:
        client.analytics(actor_id="support-1", user_role="it_support", days=30)

    assert raised.value.code == expected_code
