"""Deep module for tool registration, authorization, execution, and audit."""

import asyncio
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from enterprise_it_support.tools.contracts import (
    ToolDefinition,
    ToolExecutionAudit,
    ToolExecutionContext,
    ToolExecutionError,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolRiskLevel,
    ValidatedToolAction,
)

ToolAdapter = Callable[[BaseModel, ToolExecutionContext], Awaitable[BaseModel | dict[str, Any]]]


class ToolTransientError(RuntimeError):
    """Retryable, sanitized Adapter failure marker."""


class ToolAuditUnavailableError(RuntimeError):
    """Raised when the mandatory audit write cannot be completed."""

    def __init__(
        self,
        message: str,
        *,
        result: ToolExecutionResult | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result


class ToolAuthorizationError(RuntimeError):
    """Adapter-level resource authorization denial without sensitive detail."""


class ToolResourceNotFoundError(LookupError):
    """Adapter-level resource absence without leaking internal identifiers."""


class ToolActionValidationError(ValueError):
    """Stable validation rejection used while preparing a pending action."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ToolConfirmationValidator(Protocol):
    """Revalidate persisted confirmation evidence immediately before a write."""

    async def validate_for_execution(
        self,
        request: ToolExecutionRequest,
        definition: ToolDefinition,
    ) -> None: ...


class ToolExecutionStore(Protocol):
    """Internal persistence seam required by ToolExecutionGateway."""

    async def record(self, audit: ToolExecutionAudit) -> None: ...


class ToolPermissionPolicy(Protocol):
    """Deterministic role-to-permission policy seam."""

    def allows(self, user_role: str, required_permissions: frozenset[str]) -> bool: ...


class RolePermissionPolicy:
    """Exact role mapping used by the local MVP."""

    def __init__(self, permissions_by_role: Mapping[str, frozenset[str]]) -> None:
        self._permissions_by_role = {
            role.strip(): frozenset(permissions)
            for role, permissions in permissions_by_role.items()
            if role.strip()
        }

    def allows(self, user_role: str, required_permissions: frozenset[str]) -> bool:
        granted = self._permissions_by_role.get(user_role.strip(), frozenset())
        return required_permissions.issubset(granted)


@dataclass(frozen=True)
class _RegisteredTool:
    definition: ToolDefinition
    adapter: ToolAdapter


class ToolRegistry:
    """Allowlist of definitions and their private Adapter implementations."""

    def __init__(self) -> None:
        self._tools: dict[str, _RegisteredTool] = {}

    def register(self, definition: ToolDefinition, adapter: ToolAdapter) -> None:
        name = definition.name.strip()
        if definition.has_side_effect and definition.risk_level is not ToolRiskLevel.R1:
            raise ValueError(
                "read-only R0 tools cannot have side effects; only R1 tools may execute writes"
            )
        if not definition.has_side_effect and definition.risk_level is not ToolRiskLevel.R0:
            raise ValueError("Read-only tools must use R0 risk")
        if name in self._tools:
            raise ValueError(f"Tool is already registered: {name}")
        self._tools[name] = _RegisteredTool(definition=definition, adapter=adapter)

    def get_definition(self, name: str) -> ToolDefinition | None:
        registered = self._tools.get(name)
        return None if registered is None else registered.definition

    def list_definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(item.definition for item in self._tools.values())

    def _resolve(self, name: str) -> _RegisteredTool | None:
        return self._tools.get(name)


class MemoryToolExecutionStore:
    """In-memory audit Adapter for unit tests and isolated prototypes."""

    def __init__(self) -> None:
        self.audits: list[ToolExecutionAudit] = []

    async def record(self, audit: ToolExecutionAudit) -> None:
        self.audits.append(audit)


class ToolExecutionGateway:
    """The single tool seam visible to Agent Runtime."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        policy: ToolPermissionPolicy,
        execution_store: ToolExecutionStore,
        confirmation_validator: ToolConfirmationValidator | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._execution_store = execution_store
        self._confirmation_validator = confirmation_validator

    def validate_action(self, request: ToolExecutionRequest) -> ValidatedToolAction:
        """Validate existence, schema, and role before saving a proposed action."""
        registered = self._registry._resolve(request.tool_name)
        if registered is None:
            raise ToolActionValidationError(
                "tool_not_found",
                "Requested tool is not registered.",
            )
        definition = registered.definition
        try:
            validated_input = definition.input_schema.model_validate(request.arguments)
        except ValidationError as exception:
            raise ToolActionValidationError(
                "invalid_tool_input",
                "Tool input did not match the registered schema.",
            ) from exception
        if not self._policy.allows(
            request.context.user_role,
            definition.required_permissions,
        ):
            raise ToolActionValidationError(
                "tool_permission_denied",
                "Caller is not permitted to execute this tool.",
            )
        return ValidatedToolAction(
            definition=definition,
            arguments=validated_input.model_dump(mode="json"),
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Validate, authorize, bound, execute, sanitize, and audit one call."""
        started = monotonic()
        execution_id = uuid4()
        registered = self._registry._resolve(request.tool_name)
        if registered is None:
            result = _failure(
                execution_id=execution_id,
                tool_name=request.tool_name,
                tool_version=None,
                status=ToolExecutionStatus.NOT_FOUND,
                code="tool_not_found",
                message="Requested tool is not registered.",
                attempts=0,
                started=started,
            )
            await self._record(request, result, None, False)
            return result

        definition = registered.definition
        try:
            validated_input = definition.input_schema.model_validate(request.arguments)
        except ValidationError:
            result = _failure(
                execution_id=execution_id,
                tool_name=definition.name,
                tool_version=definition.version,
                status=ToolExecutionStatus.INVALID_INPUT,
                code="invalid_tool_input",
                message="Tool input did not match the registered schema.",
                attempts=0,
                started=started,
            )
            await self._record(
                request,
                result,
                definition.risk_level,
                definition.has_side_effect,
            )
            return result

        if not self._policy.allows(
            request.context.user_role,
            definition.required_permissions,
        ):
            result = _failure(
                execution_id=execution_id,
                tool_name=definition.name,
                tool_version=definition.version,
                status=ToolExecutionStatus.PERMISSION_DENIED,
                code="tool_permission_denied",
                message="Caller is not permitted to execute this tool.",
                attempts=0,
                started=started,
            )
            await self._record(
                request,
                result,
                definition.risk_level,
                definition.has_side_effect,
            )
            return result

        if definition.has_side_effect:
            if (
                request.context.pending_confirmation_id is None
                or request.context.idempotency_key is None
                or self._confirmation_validator is None
            ):
                result = _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.PERMISSION_DENIED,
                    code="confirmation_required",
                    message="Confirmed action evidence is required before execution.",
                    attempts=0,
                    started=started,
                )
                await self._record(
                    request,
                    result,
                    definition.risk_level,
                    definition.has_side_effect,
                )
                return result
            try:
                await self._confirmation_validator.validate_for_execution(
                    request,
                    definition,
                )
            except Exception:
                result = _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.PERMISSION_DENIED,
                    code="confirmation_invalid",
                    message="Confirmation evidence is invalid or no longer executable.",
                    attempts=0,
                    started=started,
                )
                await self._record(
                    request,
                    result,
                    definition.risk_level,
                    definition.has_side_effect,
                )
                return result

        result = await self._execute_registered(
            registered=registered,
            validated_input=validated_input,
            context=request.context,
            execution_id=execution_id,
            started=started,
        )
        await self._record(
            request,
            result,
            definition.risk_level,
            definition.has_side_effect,
        )
        return result

    async def _execute_registered(
        self,
        *,
        registered: _RegisteredTool,
        validated_input: BaseModel,
        context: ToolExecutionContext,
        execution_id: Any,
        started: float,
    ) -> ToolExecutionResult:
        definition = registered.definition
        policy = definition.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            try:
                async with asyncio.timeout(definition.timeout_seconds):
                    raw_output = await registered.adapter(
                        validated_input,
                        replace(context, execution_id=execution_id),
                    )
            except TimeoutError:
                if attempt < policy.max_attempts and policy.retry_on_timeout:
                    await _backoff(policy.backoff_seconds)
                    continue
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.TIMED_OUT,
                    code="tool_timeout",
                    message="Tool execution exceeded its time limit.",
                    attempts=attempt,
                    started=started,
                )
            except ToolTransientError:
                if attempt < policy.max_attempts and policy.retry_on_transient_error:
                    await _backoff(policy.backoff_seconds)
                    continue
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.FAILED,
                    code="tool_transient_failure",
                    message="Tool remained unavailable after bounded retries.",
                    attempts=attempt,
                    started=started,
                )
            except ToolAuthorizationError:
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.PERMISSION_DENIED,
                    code="tool_resource_permission_denied",
                    message="Caller is not permitted to access this resource.",
                    attempts=attempt,
                    started=started,
                )
            except ToolResourceNotFoundError:
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.NOT_FOUND,
                    code="tool_resource_not_found",
                    message="Requested tool resource was not found.",
                    attempts=attempt,
                    started=started,
                )
            except Exception:
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.FAILED,
                    code="tool_execution_failed",
                    message="Tool execution failed safely.",
                    attempts=attempt,
                    started=started,
                )

            try:
                output = definition.output_schema.model_validate(raw_output)
            except ValidationError:
                return _failure(
                    execution_id=execution_id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    status=ToolExecutionStatus.FAILED,
                    code="invalid_tool_output",
                    message="Tool output did not match the registered schema.",
                    attempts=attempt,
                    started=started,
                )
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_name=definition.name,
                tool_version=definition.version,
                status=ToolExecutionStatus.SUCCEEDED,
                observation=output.model_dump(mode="json"),
                error=None,
                attempts=attempt,
                latency_ms=_latency_ms(started),
            )
        raise AssertionError("Tool retry loop exhausted unexpectedly")

    async def _record(
        self,
        request: ToolExecutionRequest,
        result: ToolExecutionResult,
        risk_level: Any,
        has_side_effect: bool,
    ) -> None:
        audit_result = ToolExecutionResult(
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            tool_version=result.tool_version,
            status=result.status,
            observation=(
                None if result.observation is None else _sanitize_json(result.observation)
            ),
            error=result.error,
            attempts=result.attempts,
            latency_ms=result.latency_ms,
        )
        audit = ToolExecutionAudit(
            result=audit_result,
            context=request.context,
            arguments=_sanitize_json(request.arguments),
            risk_level=risk_level,
            has_side_effect=has_side_effect,
        )
        try:
            await self._execution_store.record(audit)
        except Exception as exception:
            raise ToolAuditUnavailableError(
                "Tool audit storage is unavailable",
                result=result,
            ) from exception


def _failure(
    *,
    execution_id: Any,
    tool_name: str,
    tool_version: str | None,
    status: ToolExecutionStatus,
    code: str,
    message: str,
    attempts: int,
    started: float,
) -> ToolExecutionResult:
    return ToolExecutionResult(
        execution_id=execution_id,
        tool_name=tool_name,
        tool_version=tool_version,
        status=status,
        observation=None,
        error=ToolExecutionError(code=code, message=message),
        attempts=attempts,
        latency_ms=_latency_ms(started),
    )


async def _backoff(seconds: float) -> None:
    if seconds > 0:
        await asyncio.sleep(seconds)


def _latency_ms(started: float) -> int:
    return max(0, int((monotonic() - started) * 1000))


def _sanitize_json(value: Any, *, depth: int = 0) -> Any:
    """Keep audit inputs bounded and redact common secret-shaped keys."""
    if depth >= 5:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in list(value.items())[:50]:
            normalized = str(key).casefold()
            if any(token in normalized for token in ("password", "secret", "token", "api_key")):
                sanitized[str(key)] = "[REDACTED]"
            elif normalized in {
                "body",
                "comment",
                "content",
                "description",
                "diagnosis_summary",
                "title",
            }:
                sanitized[str(key)] = _text_summary(item)
            else:
                sanitized[str(key)] = _sanitize_json(item, depth=depth + 1)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return _redact_text(value[:500]) if isinstance(value, str) else value
    return str(value)[:500]


def _text_summary(value: Any) -> dict[str, int | str]:
    text = value if isinstance(value, str) else str(value)
    return {"redacted": "[TEXT REDACTED]", "length": len(text)}


def _redact_text(value: str) -> str:
    patterns = (
        r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+",
        r"(?i)\b(password|token|secret|api[_-]?key)\s*[:=]\s*\S+",
    )
    redacted = value
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted
