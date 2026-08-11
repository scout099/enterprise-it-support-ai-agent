"""Bounded structured-output gateway for chat models."""

import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

ResponseT = TypeVar("ResponseT", bound=BaseModel)
Sleeper = Callable[[float], Awaitable[None]]


class ModelGatewayError(RuntimeError):
    """Base class for safe model-boundary failures."""


class ModelGatewayTimeoutError(ModelGatewayError):
    """Raised after all bounded model attempts time out."""


class ModelGatewayUnavailableError(ModelGatewayError):
    """Raised when the configured provider cannot complete a request."""


class ModelGatewayResponseError(ModelGatewayError):
    """Raised when provider output does not satisfy the requested schema."""


@dataclass(frozen=True)
class ModelMessage:
    """One role-scoped message passed to the provider."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class TokenUsage:
    """Provider-reported token counts, using zero when unavailable."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass(frozen=True)
class ModelCallMetadata:
    """Observable model identity, prompt version, usage, and attempt count."""

    provider: str
    configured_model: str
    resolved_model: str
    prompt_version: str
    usage: TokenUsage
    attempts: int


@dataclass(frozen=True)
class StructuredModelResponse[ResponseT: BaseModel]:
    """Validated structured value plus provider metadata."""

    value: ResponseT
    metadata: ModelCallMetadata


class ModelGateway(Protocol):
    """Provider-neutral structured generation boundary."""

    @property
    def model_name(self) -> str: ...

    async def generate_structured_response(
        self,
        *,
        messages: Sequence[ModelMessage],
        response_schema: type[ResponseT],
        prompt_version: str,
    ) -> StructuredModelResponse[ResponseT]: ...


@dataclass(frozen=True)
class FakeModelCall:
    """One observable invocation recorded by the deterministic fake."""

    messages: tuple[ModelMessage, ...]
    response_schema: type[BaseModel]
    prompt_version: str


FakeResponseFactory = Callable[[FakeModelCall], BaseModel | dict[str, Any]]


class FakeModelGateway:
    """Return queued deterministic values without any external model call."""

    def __init__(
        self,
        responses: Sequence[BaseModel | dict[str, Any] | Exception],
        *,
        model_name: str = "fake-chat-v1",
        usage: TokenUsage | None = None,
        response_factory: FakeResponseFactory | None = None,
    ) -> None:
        self._responses = list(responses)
        self._model_name = model_name
        self._usage = usage or TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30)
        self._response_factory = response_factory
        self.calls: list[FakeModelCall] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_structured_response(
        self,
        *,
        messages: Sequence[ModelMessage],
        response_schema: type[ResponseT],
        prompt_version: str,
    ) -> StructuredModelResponse[ResponseT]:
        call = FakeModelCall(
            messages=tuple(messages),
            response_schema=response_schema,
            prompt_version=prompt_version,
        )
        self.calls.append(call)
        if self._responses:
            outcome = self._responses.pop(0)
        elif self._response_factory is not None:
            outcome = self._response_factory(call)
        else:
            raise ModelGatewayUnavailableError("Fake model has no queued response")
        if isinstance(outcome, Exception):
            raise outcome
        try:
            value = response_schema.model_validate(outcome)
        except ValidationError as exception:
            raise ModelGatewayResponseError(
                "Model response failed schema validation"
            ) from exception
        return StructuredModelResponse(
            value=value,
            metadata=ModelCallMetadata(
                provider="fake",
                configured_model=self._model_name,
                resolved_model=self._model_name,
                prompt_version=prompt_version,
                usage=self._usage,
                attempts=1,
            ),
        )


class OpenAICompatibleModelGateway:
    """Call an OpenAI-compatible Chat Completions structured-output endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_attempts: int,
        max_output_tokens: int,
        retry_backoff_seconds: float = 0.25,
        client: Any | None = None,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Model timeout must be positive")
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("Model max attempts must be between 1 and 5")
        if max_output_tokens < 1:
            raise ValueError("Model output token limit must be positive")
        if retry_backoff_seconds < 0:
            raise ValueError("Model retry backoff cannot be negative")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._max_output_tokens = max_output_tokens
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleeper = sleeper
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_structured_response(
        self,
        *,
        messages: Sequence[ModelMessage],
        response_schema: type[ResponseT],
        prompt_version: str,
    ) -> StructuredModelResponse[ResponseT]:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": message.role, "content": message.content}
                            for message in messages
                        ],
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_schema.__name__,
                                "strict": True,
                                "schema": response_schema.model_json_schema(),
                            },
                        },
                        max_completion_tokens=self._max_output_tokens,
                        temperature=0,
                        timeout=self._timeout_seconds,
                    ),
                    timeout=self._timeout_seconds,
                )
            except (TimeoutError, APITimeoutError) as exception:
                if attempt == self._max_attempts:
                    raise ModelGatewayTimeoutError("Model request timed out") from exception
                await self._backoff(attempt)
                continue
            except (APIConnectionError, RateLimitError) as exception:
                if attempt == self._max_attempts:
                    raise ModelGatewayUnavailableError(
                        "Model provider is temporarily unavailable"
                    ) from exception
                await self._backoff(attempt)
                continue
            except APIStatusError as exception:
                if exception.status_code >= 500 and attempt < self._max_attempts:
                    await self._backoff(attempt)
                    continue
                raise ModelGatewayUnavailableError(
                    "Model provider rejected the request"
                ) from exception
            except Exception as exception:
                raise ModelGatewayUnavailableError("Model provider request failed") from exception

            return self._validate_response(
                response,
                response_schema=response_schema,
                prompt_version=prompt_version,
                attempts=attempt,
            )

        raise AssertionError("bounded model attempt loop did not terminate")

    async def _backoff(self, attempt: int) -> None:
        await self._sleeper(min(self._retry_backoff_seconds * (2 ** (attempt - 1)), 2.0))

    def _validate_response(
        self,
        response: Any,
        *,
        response_schema: type[ResponseT],
        prompt_version: str,
        attempts: int,
    ) -> StructuredModelResponse[ResponseT]:
        try:
            content = response.choices[0].message.content
            if not content:
                raise ValueError("empty response content")
            value = response_schema.model_validate(json.loads(content))
        except (
            AttributeError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as exception:
            raise ModelGatewayResponseError(
                "Model response failed schema validation"
            ) from exception

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        reported_total = getattr(usage, "total_tokens", None)
        total_tokens = (
            input_tokens + output_tokens if reported_total is None else int(reported_total)
        )
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)
        return StructuredModelResponse(
            value=value,
            metadata=ModelCallMetadata(
                provider="openai_compatible",
                configured_model=self._model,
                resolved_model=str(getattr(response, "model", self._model)),
                prompt_version=prompt_version,
                usage=TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cached_tokens=int(getattr(prompt_details, "cached_tokens", 0) or 0),
                    reasoning_tokens=int(getattr(completion_details, "reasoning_tokens", 0) or 0),
                ),
                attempts=attempts,
            ),
        )
