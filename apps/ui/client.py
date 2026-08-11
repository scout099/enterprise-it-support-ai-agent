"""Small HTTP-only client used by Streamlit pages."""

from typing import Any
from uuid import UUID, uuid4

import requests


class APIError(RuntimeError):
    """A safe FastAPI error returned to the UI."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class ITSupportAPIClient:
    """Call only public FastAPI endpoints; never access persistence directly."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        normalized = base_url.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("API base URL must use http or https")
        self._base_url = normalized
        self._timeout_seconds = timeout_seconds
        self._session = session or requests.Session()

    def respond(
        self,
        *,
        user_message: str,
        actor_id: str,
        user_role: str,
        conversation_id: str | None,
        ticket_number: str | None = None,
        business_justification: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "user_message": user_message,
            "actor_id": actor_id,
            "user_role": user_role,
            "idempotency_key": f"ui-{uuid4()}",
        }
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id
        if ticket_number is not None:
            payload["ticket_number"] = ticket_number
        if business_justification is not None:
            payload["business_justification"] = business_justification
        return self._request("POST", "/agent/respond", json=payload)

    def confirm(self, *, confirmation_id: str, actor_id: str, user_role: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/agent/confirm",
            json={
                "confirmation_id": confirmation_id,
                "actor_id": actor_id,
                "user_role": user_role,
            },
        )

    def agent_run(self, *, run_id: str, user_role: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/agent/runs/{UUID(run_id)}",
            params={"user_role": user_role},
        )

    def cancel(self, *, confirmation_id: str, actor_id: str, user_role: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/agent/cancel",
            json={
                "confirmation_id": confirmation_id,
                "actor_id": actor_id,
                "user_role": user_role,
            },
        )

    def submit_feedback(
        self,
        *,
        agent_run_id: str,
        actor_id: str,
        user_role: str,
        resolved: bool,
        satisfaction_rating: int,
        comment: str | None,
        ticket_number: str | None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/feedback",
            json={
                "agent_run_id": agent_run_id,
                "actor_id": actor_id,
                "user_role": user_role,
                "resolved": resolved,
                "satisfaction_rating": satisfaction_rating,
                "comment": comment,
                "ticket_number": ticket_number,
                "idempotency_key": f"ui-feedback-{UUID(agent_run_id)}",
            },
        )

    def analytics(
        self,
        *,
        actor_id: str,
        user_role: str,
        days: int,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/analytics/summary",
            params={"actor_id": actor_id, "user_role": user_role, "days": days},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._session.request(
                method,
                f"{self._base_url}{path}",
                timeout=self._timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exception:
            raise APIError(0, "api_unavailable", "FastAPI is unavailable") from exception
        if response.status_code >= 400:
            code = "api_error"
            message = f"FastAPI returned HTTP {response.status_code}"
            try:
                body = response.json()
                error = body.get("error", body)
                code = str(error.get("code", code))
                message = str(error.get("message", message))
            except (ValueError, AttributeError):
                pass
            raise APIError(response.status_code, code, message)
        try:
            payload = response.json()
        except ValueError as exception:
            raise APIError(
                response.status_code,
                "invalid_api_response",
                "FastAPI returned invalid JSON",
            ) from exception
        if not isinstance(payload, dict):
            raise APIError(
                response.status_code,
                "invalid_api_response",
                "FastAPI returned an unexpected response",
            )
        return payload
