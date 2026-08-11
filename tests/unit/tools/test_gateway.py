"""Tool Registry and Gateway behavior through their public interface."""

import asyncio
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from enterprise_it_support.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionStatus,
    ToolRiskLevel,
)
from enterprise_it_support.tools.gateway import (
    MemoryToolExecutionStore,
    RolePermissionPolicy,
    ToolExecutionGateway,
    ToolRegistry,
    ToolTransientError,
)
from enterprise_it_support.tools.mock import (
    KnowledgeItem,
    create_mock_tool_registry,
    default_tool_permissions,
)


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: int
    api_key: str | None = None


class OutputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    doubled: int


def definition(
    *,
    timeout_seconds: float = 1,
    retry_policy: RetryPolicy | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name="test_tool",
        version="1.2.3",
        description="A deterministic test tool.",
        input_schema=InputSchema,
        output_schema=OutputSchema,
        required_permissions=frozenset({"test:read"}),
        risk_level=ToolRiskLevel.LOW,
        has_side_effect=False,
        timeout_seconds=timeout_seconds,
        retry_policy=retry_policy or RetryPolicy(),
    )


def context(*, role: str = "employee") -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id=uuid4(),
        request_id="tool-request",
        node_name="test_node",
        user_role=role,
    )


def gateway(
    adapter: Any,
    *,
    tool_definition: ToolDefinition | None = None,
    permissions: frozenset[str] = frozenset({"test:read"}),
) -> tuple[ToolExecutionGateway, MemoryToolExecutionStore]:
    registry = ToolRegistry()
    registry.register(tool_definition or definition(), adapter)
    store = MemoryToolExecutionStore()
    return (
        ToolExecutionGateway(
            registry=registry,
            policy=RolePermissionPolicy({"employee": permissions}),
            execution_store=store,
        ),
        store,
    )


async def test_registry_exposes_all_seven_read_only_mock_definitions() -> None:
    registry = create_mock_tool_registry()
    definitions = registry.list_definitions()

    assert {item.name for item in definitions} == {
        "get_account_status",
        "get_mail_service_status",
        "get_vpn_service_status",
        "get_device_info",
        "run_mock_network_check",
        "search_existing_incidents",
        "search_knowledge",
    }
    assert all(item.version == "1.0.0" for item in definitions)
    assert all(item.description for item in definitions)
    assert all(item.input_schema.model_json_schema() for item in definitions)
    assert all(item.output_schema.model_json_schema() for item in definitions)
    assert all(item.required_permissions for item in definitions)
    assert all(item.risk_level is ToolRiskLevel.LOW for item in definitions)
    assert all(item.has_side_effect is False for item in definitions)
    assert all(item.timeout_seconds > 0 for item in definitions)
    assert all(item.retry_policy.max_attempts == 2 for item in definitions)


async def test_registry_rejects_duplicates_and_side_effect_tools() -> None:
    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        return {"doubled": 2}

    registry = ToolRegistry()
    registry.register(definition(), adapter)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition(), adapter)
    with pytest.raises(ValueError, match="read-only"):
        ToolRegistry().register(replace(definition(), has_side_effect=True), adapter)


def test_mock_knowledge_step_has_a_finite_output_bound() -> None:
    with pytest.raises(ValidationError):
        KnowledgeItem(article_id="KB-1", title="Bounded", steps=["x" * 501])


async def test_gateway_rejects_unknown_tool_and_records_attempt() -> None:
    registry = ToolRegistry()
    store = MemoryToolExecutionStore()
    tool_gateway = ToolExecutionGateway(
        registry=registry,
        policy=RolePermissionPolicy(default_tool_permissions()),
        execution_store=store,
    )

    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="arbitrary_python_function",
            arguments={},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.NOT_FOUND
    assert result.error is not None
    assert result.error.code == "tool_not_found"
    assert result.observation is None
    assert len(store.audits) == 1
    assert store.audits[0].result == result


async def test_gateway_rejects_invalid_parameters_before_adapter_call() -> None:
    calls = 0

    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"doubled": 2}

    tool_gateway, store = gateway(adapter)
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 1, "unexpected": True},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.INVALID_INPUT
    assert result.attempts == 0
    assert calls == 0
    assert store.audits[0].result.status is ToolExecutionStatus.INVALID_INPUT


async def test_gateway_denies_missing_permission_before_adapter_call() -> None:
    calls = 0

    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"doubled": 2}

    tool_gateway, store = gateway(adapter, permissions=frozenset())
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 1},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.PERMISSION_DENIED
    assert result.error is not None
    assert result.error.code == "tool_permission_denied"
    assert calls == 0
    assert store.audits[0].result.status is ToolExecutionStatus.PERMISSION_DENIED


async def test_gateway_times_out_with_finite_attempts() -> None:
    calls = 0

    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.1)
        return {"doubled": 2}

    tool_gateway, store = gateway(
        adapter,
        tool_definition=definition(
            timeout_seconds=0.01,
            retry_policy=RetryPolicy(max_attempts=2),
        ),
    )
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 1},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.TIMED_OUT
    assert result.attempts == 2
    assert calls == 2
    assert len(store.audits) == 1


async def test_gateway_retries_transient_error_then_returns_validated_observation() -> None:
    calls = 0

    async def adapter(value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ToolTransientError("fictional raw detail")
        parsed = InputSchema.model_validate(value)
        return {"doubled": parsed.value * 2}

    tool_gateway, store = gateway(
        adapter,
        tool_definition=definition(retry_policy=RetryPolicy(max_attempts=2)),
    )
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 4},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.SUCCEEDED
    assert result.attempts == 2
    assert result.observation == {"doubled": 8}
    assert len(store.audits) == 1


async def test_gateway_rejects_coerced_or_invalid_adapter_output() -> None:
    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, str]:
        return {"doubled": "2"}

    tool_gateway, store = gateway(adapter)
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 1},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "invalid_tool_output"
    assert result.observation is None
    assert store.audits[0].result == result


async def test_gateway_cleans_adapter_errors_and_redacts_audit_arguments() -> None:
    async def adapter(_value: BaseModel, _context: ToolExecutionContext) -> dict[str, int]:
        raise RuntimeError("fictional-provider-secret")

    tool_gateway, store = gateway(adapter)
    result = await tool_gateway.execute(
        ToolExecutionRequest(
            tool_name="test_tool",
            arguments={"value": 1, "api_key": "fictional-api-key"},
            context=context(),
        )
    )

    assert result.status is ToolExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "tool_execution_failed"
    assert "fictional" not in str(result)
    assert store.audits[0].arguments["api_key"] == "[REDACTED]"
