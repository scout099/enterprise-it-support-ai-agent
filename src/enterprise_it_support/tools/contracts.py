"""Public contracts for registered, bounded, read-only tool execution."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ToolRiskLevel(StrEnum):
    """Risk metadata enforced by deterministic code."""

    R0 = "r0"
    R1 = "r1"
    R3 = "r3"
    LOW = "r0"
    MEDIUM = "r1"
    HIGH = "r3"


class ToolExecutionStatus(StrEnum):
    """Stable outcomes exposed to Agent state and audit storage."""

    SUCCEEDED = "succeeded"
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass(frozen=True)
class RetryPolicy:
    """Finite retry policy owned by one tool definition."""

    max_attempts: int = 1
    backoff_seconds: float = 0.0
    retry_on_timeout: bool = True
    retry_on_transient_error: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("Tool retry attempts must be between one and five")
        if not 0 <= self.backoff_seconds <= 5:
            raise ValueError("Tool retry backoff must be between zero and five seconds")


@dataclass(frozen=True)
class ToolDefinition:
    """Allowlisted tool metadata and strict input/output contracts."""

    name: str
    version: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_permissions: frozenset[str]
    risk_level: ToolRiskLevel
    has_side_effect: bool
    timeout_seconds: float
    retry_policy: RetryPolicy

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip() or not self.description.strip():
            raise ValueError("Tool name, version, and description are required")
        if not 0 < self.timeout_seconds <= 120:
            raise ValueError("Tool timeout must be between zero and 120 seconds")


@dataclass(frozen=True)
class ToolExecutionContext:
    """Deterministic caller context used for authorization and traceability."""

    run_id: UUID | None
    request_id: str
    node_name: str
    user_role: str
    actor_id: str | None = None
    pending_confirmation_id: UUID | None = None
    idempotency_key: str | None = None
    execution_id: UUID | None = None


@dataclass(frozen=True)
class ToolExecutionRequest:
    """The only request accepted by ToolExecutionGateway."""

    tool_name: str
    arguments: dict[str, Any]
    context: ToolExecutionContext


@dataclass(frozen=True)
class ToolExecutionError:
    """Safe error without Adapter exception text or raw logs."""

    code: str
    message: str


@dataclass(frozen=True)
class ToolExecutionResult:
    """Structured observation or stable failure from one logical tool call."""

    execution_id: UUID
    tool_name: str
    tool_version: str | None
    status: ToolExecutionStatus
    observation: dict[str, Any] | None
    error: ToolExecutionError | None
    attempts: int
    latency_ms: int

    @property
    def succeeded(self) -> bool:
        return self.status is ToolExecutionStatus.SUCCEEDED

    def as_state_value(self) -> dict[str, Any]:
        """Serialize the bounded result for AgentState and checkpoints."""
        return {
            "execution_id": str(self.execution_id),
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "status": self.status.value,
            "observation": self.observation,
            "error": (
                None
                if self.error is None
                else {"code": self.error.code, "message": self.error.message}
            ),
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class ToolExecutionAudit:
    """Persistence command for one final logical tool-call outcome."""

    result: ToolExecutionResult
    context: ToolExecutionContext
    arguments: dict[str, Any]
    risk_level: ToolRiskLevel | None
    has_side_effect: bool


@dataclass(frozen=True)
class ValidatedToolAction:
    """A schema-validated, authorized action preview before persistence."""

    definition: ToolDefinition
    arguments: dict[str, Any]
