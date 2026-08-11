"""Structured model gateway contract tests."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError
from pydantic import BaseModel

from enterprise_it_support.agent_runtime.rag import RAGModelOutput
from enterprise_it_support.intelligence.model_gateway import (
    FakeModelGateway,
    ModelGatewayResponseError,
    ModelGatewayTimeoutError,
    ModelGatewayUnavailableError,
    ModelMessage,
    OpenAICompatibleModelGateway,
    TokenUsage,
)


class ExampleResponse(BaseModel):
    value: str


def test_rag_model_output_schema_requires_every_declared_field() -> None:
    schema = RAGModelOutput.model_json_schema()

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


class StubCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, float):
            await asyncio.sleep(outcome)
            raise AssertionError("wait_for should cancel the slow provider call")
        return outcome


def stub_client(outcomes):
    completions = StubCompletions(outcomes)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def provider_response(content: str):
    usage = SimpleNamespace(
        prompt_tokens=11,
        completion_tokens=7,
        total_tokens=18,
        prompt_tokens_details=SimpleNamespace(cached_tokens=2),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=3),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=usage,
        model="resolved-test-model",
    )


@pytest.mark.asyncio
async def test_fake_model_gateway_validates_output_and_records_metadata() -> None:
    gateway = FakeModelGateway(
        [{"value": "grounded"}],
        usage=TokenUsage(input_tokens=4, output_tokens=5, total_tokens=9),
    )

    response = await gateway.generate_structured_response(
        messages=[ModelMessage(role="user", content="question")],
        response_schema=ExampleResponse,
        prompt_version="prompt-v1",
    )

    assert response.value == ExampleResponse(value="grounded")
    assert response.metadata.configured_model == "fake-chat-v1"
    assert response.metadata.prompt_version == "prompt-v1"
    assert response.metadata.usage.total_tokens == 9
    assert gateway.calls[0].messages[0].content == "question"


@pytest.mark.asyncio
async def test_fake_model_gateway_rejects_invalid_structured_output() -> None:
    gateway = FakeModelGateway([{"wrong": "shape"}])

    with pytest.raises(ModelGatewayResponseError):
        await gateway.generate_structured_response(
            messages=[ModelMessage(role="user", content="question")],
            response_schema=ExampleResponse,
            prompt_version="prompt-v1",
        )


@pytest.mark.asyncio
async def test_openai_compatible_gateway_retries_transient_failure_and_records_usage() -> None:
    connection_error = APIConnectionError(request=httpx.Request("POST", "https://example.test"))
    client, completions = stub_client([connection_error, provider_response('{"value":"grounded"}')])
    sleeps = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    gateway = OpenAICompatibleModelGateway(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="configured-test-model",
        timeout_seconds=1,
        max_attempts=2,
        max_output_tokens=100,
        client=client,
        sleeper=fake_sleep,
    )

    response = await gateway.generate_structured_response(
        messages=[ModelMessage(role="system", content="rules")],
        response_schema=ExampleResponse,
        prompt_version="prompt-v1",
    )

    assert len(completions.calls) == 2
    assert sleeps == [0.25]
    assert response.value.value == "grounded"
    assert response.metadata.attempts == 2
    assert response.metadata.resolved_model == "resolved-test-model"
    assert response.metadata.usage == TokenUsage(
        input_tokens=11,
        output_tokens=7,
        total_tokens=18,
        cached_tokens=2,
        reasoning_tokens=3,
    )
    assert completions.calls[1]["response_format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_openai_compatible_gateway_bounds_timeout_retries() -> None:
    client, completions = stub_client([0.05, 0.05])

    async def no_sleep(_seconds: float) -> None:
        return None

    gateway = OpenAICompatibleModelGateway(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="configured-test-model",
        timeout_seconds=0.001,
        max_attempts=2,
        max_output_tokens=100,
        client=client,
        sleeper=no_sleep,
    )

    with pytest.raises(ModelGatewayTimeoutError) as captured:
        await gateway.generate_structured_response(
            messages=[ModelMessage(role="user", content="question")],
            response_schema=ExampleResponse,
            prompt_version="prompt-v1",
        )

    assert len(completions.calls) == 2
    assert captured.value.metadata is not None
    assert captured.value.metadata.attempts == 2
    assert captured.value.metadata.prompt_version == "prompt-v1"
    assert captured.value.metadata.usage == TokenUsage()


@pytest.mark.asyncio
async def test_openai_compatible_gateway_does_not_retry_malformed_output() -> None:
    client, completions = stub_client([provider_response("not-json")])
    gateway = OpenAICompatibleModelGateway(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="configured-test-model",
        timeout_seconds=1,
        max_attempts=3,
        max_output_tokens=100,
        client=client,
    )

    with pytest.raises(ModelGatewayResponseError) as captured:
        await gateway.generate_structured_response(
            messages=[ModelMessage(role="user", content="question")],
            response_schema=ExampleResponse,
            prompt_version="prompt-v1",
        )

    assert len(completions.calls) == 1
    assert captured.value.metadata is not None
    assert captured.value.metadata.attempts == 1
    assert captured.value.metadata.usage.total_tokens == 18


@pytest.mark.asyncio
async def test_openai_compatible_gateway_records_exhausted_provider_attempts() -> None:
    connection_error = APIConnectionError(request=httpx.Request("POST", "https://example.test"))
    client, completions = stub_client([connection_error, connection_error])

    async def no_sleep(_seconds: float) -> None:
        return None

    gateway = OpenAICompatibleModelGateway(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="configured-test-model",
        timeout_seconds=1,
        max_attempts=2,
        max_output_tokens=100,
        client=client,
        sleeper=no_sleep,
    )

    with pytest.raises(ModelGatewayUnavailableError) as captured:
        await gateway.generate_structured_response(
            messages=[ModelMessage(role="user", content="question")],
            response_schema=ExampleResponse,
            prompt_version="prompt-v1",
        )

    assert len(completions.calls) == 2
    assert captured.value.metadata is not None
    assert captured.value.metadata.attempts == 2
    assert captured.value.metadata.configured_model == "configured-test-model"
