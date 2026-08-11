"""Deterministic read-only Mock tools for local diagnostic workflows."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from enterprise_it_support.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
    ToolRiskLevel,
)
from enterprise_it_support.tools.gateway import ToolRegistry


class ServiceHealth(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"


class MFAState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class OSFamily(StrEnum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


class KnowledgeArea(StrEnum):
    VPN = "vpn"
    OUTLOOK = "outlook"
    ACCOUNT = "account"


class IncidentService(StrEnum):
    VPN = "vpn"
    MAIL = "mail"
    IDENTITY = "identity"


class StrictToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AccountStatusInput(StrictToolModel):
    account_ref: str = Field(default="current", min_length=1, max_length=100)


class AccountStatusOutput(StrictToolModel):
    account_ref: str = Field(min_length=1, max_length=100)
    locked: bool
    password_expired: bool
    mfa_state: Annotated[MFAState, Field(strict=False)]
    status_source: str = Field(default="mock_directory", min_length=1, max_length=100)


class ServiceStatusInput(StrictToolModel):
    region: str = Field(default="global", min_length=1, max_length=100)


class ServiceStatusOutput(StrictToolModel):
    service: str = Field(min_length=1, max_length=50)
    region: str = Field(min_length=1, max_length=100)
    status: Annotated[ServiceHealth, Field(strict=False)]
    advisory: str | None = Field(default=None, max_length=500)


class DeviceInfoInput(StrictToolModel):
    device_ref: str = Field(default="current", min_length=1, max_length=100)


class DeviceInfoOutput(StrictToolModel):
    device_ref: str = Field(min_length=1, max_length=100)
    os_family: Annotated[OSFamily, Field(strict=False)]
    os_version: str = Field(min_length=1, max_length=100)
    vpn_client_installed: bool
    vpn_client_running: bool
    outlook_client_installed: bool


class NetworkCheckInput(StrictToolModel):
    target: str = Field(default="internet", pattern=r"^internet$")


class NetworkCheckOutput(StrictToolModel):
    target: str = Field(pattern=r"^internet$", max_length=20)
    reachable: bool
    latency_ms: int | None = Field(default=None, ge=0, le=60000)
    check_source: str = Field(default="mock_network_probe", min_length=1, max_length=100)


class IncidentSearchInput(StrictToolModel):
    service: Annotated[IncidentService, Field(strict=False)]


class IncidentItem(StrictToolModel):
    incident_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    status: str = Field(min_length=1, max_length=50)
    severity: str = Field(min_length=1, max_length=50)


class IncidentSearchOutput(StrictToolModel):
    service: Annotated[IncidentService, Field(strict=False)]
    incidents: list[IncidentItem] = Field(max_length=10)


class KnowledgeSearchInput(StrictToolModel):
    area: Annotated[KnowledgeArea, Field(strict=False)]
    query: str = Field(min_length=1, max_length=500)


class KnowledgeItem(StrictToolModel):
    article_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    steps: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1,
        max_length=8,
    )


class KnowledgeSearchOutput(StrictToolModel):
    area: Annotated[KnowledgeArea, Field(strict=False)]
    results: list[KnowledgeItem] = Field(max_length=5)


@dataclass
class MockITEnvironment:
    """Configurable local facts returned by all seven Mock Adapters."""

    account_status: AccountStatusOutput = field(
        default_factory=lambda: AccountStatusOutput(
            account_ref="current",
            locked=False,
            password_expired=False,
            mfa_state=MFAState.ENABLED,
        )
    )
    mail_status: ServiceStatusOutput = field(
        default_factory=lambda: ServiceStatusOutput(
            service="mail",
            region="global",
            status=ServiceHealth.OPERATIONAL,
        )
    )
    vpn_status: ServiceStatusOutput = field(
        default_factory=lambda: ServiceStatusOutput(
            service="vpn",
            region="global",
            status=ServiceHealth.OPERATIONAL,
        )
    )
    device_info: DeviceInfoOutput = field(
        default_factory=lambda: DeviceInfoOutput(
            device_ref="current",
            os_family=OSFamily.MACOS,
            os_version="14.6",
            vpn_client_installed=True,
            vpn_client_running=True,
            outlook_client_installed=True,
        )
    )
    network_check: NetworkCheckOutput = field(
        default_factory=lambda: NetworkCheckOutput(
            target="internet",
            reachable=True,
            latency_ms=25,
        )
    )
    incidents: dict[IncidentService, list[IncidentItem]] = field(default_factory=dict)
    knowledge: dict[KnowledgeArea, list[KnowledgeItem]] = field(
        default_factory=lambda: {
            KnowledgeArea.VPN: [
                KnowledgeItem(
                    article_id="KB-MOCK-VPN-001",
                    title="Mock VPN client recovery",
                    steps=[
                        "Confirm normal internet access before reconnecting.",
                        "Start the approved VPN client and retry once.",
                    ],
                )
            ],
            KnowledgeArea.OUTLOOK: [
                KnowledgeItem(
                    article_id="KB-MOCK-MAIL-001",
                    title="Mock Outlook mail troubleshooting",
                    steps=[
                        "Compare the desktop client with the Web experience.",
                        "Record any visible error code before contacting IT.",
                    ],
                )
            ],
            KnowledgeArea.ACCOUNT: [
                KnowledgeItem(
                    article_id="KB-MOCK-ID-001",
                    title="Mock account recovery guidance",
                    steps=[
                        "Use the approved password reset or unlock channel.",
                        "Confirm MFA enrollment after access is restored.",
                    ],
                )
            ],
        }
    )


def create_mock_tool_registry(
    environment: MockITEnvironment | None = None,
    registry: ToolRegistry | None = None,
) -> ToolRegistry:
    """Register exactly the seven Phase 7 read-only Mock tools."""
    data = environment or MockITEnvironment()
    registry = registry or ToolRegistry()
    _register(
        registry,
        name="get_account_status",
        description="Read a mock account lock, password, and MFA status.",
        input_schema=AccountStatusInput,
        output_schema=AccountStatusOutput,
        permission="account:read",
        adapter=lambda value, _context: _value(data.account_status, account_ref=value.account_ref),
    )
    _register(
        registry,
        name="get_mail_service_status",
        description="Read the mock enterprise mail-service health.",
        input_schema=ServiceStatusInput,
        output_schema=ServiceStatusOutput,
        permission="mail:read",
        adapter=lambda value, _context: _value(data.mail_status, region=value.region),
    )
    _register(
        registry,
        name="get_vpn_service_status",
        description="Read the mock enterprise VPN-service health.",
        input_schema=ServiceStatusInput,
        output_schema=ServiceStatusOutput,
        permission="vpn:read",
        adapter=lambda value, _context: _value(data.vpn_status, region=value.region),
    )
    _register(
        registry,
        name="get_device_info",
        description="Read mock operating-system and approved-client state.",
        input_schema=DeviceInfoInput,
        output_schema=DeviceInfoOutput,
        permission="device:read",
        adapter=lambda value, _context: _value(data.device_info, device_ref=value.device_ref),
    )
    _register(
        registry,
        name="run_mock_network_check",
        description="Run a mock read-only public-internet reachability check.",
        input_schema=NetworkCheckInput,
        output_schema=NetworkCheckOutput,
        permission="network:check",
        adapter=lambda value, _context: _value(data.network_check, target=value.target),
    )
    _register(
        registry,
        name="search_existing_incidents",
        description="Search bounded mock incidents for one enterprise service.",
        input_schema=IncidentSearchInput,
        output_schema=IncidentSearchOutput,
        permission="incidents:read",
        adapter=lambda value, _context: IncidentSearchOutput(
            service=value.service,
            incidents=data.incidents.get(value.service, []),
        ),
    )
    _register(
        registry,
        name="search_knowledge",
        description="Search bounded mock diagnostic knowledge steps.",
        input_schema=KnowledgeSearchInput,
        output_schema=KnowledgeSearchOutput,
        permission="knowledge:read",
        adapter=lambda value, _context: KnowledgeSearchOutput(
            area=value.area,
            results=data.knowledge.get(value.area, []),
        ),
    )
    return registry


def default_tool_permissions() -> dict[str, frozenset[str]]:
    """Local-role permissions; all grants are read-only."""
    read_permissions = frozenset(
        {
            "account:read",
            "mail:read",
            "vpn:read",
            "device:read",
            "network:check",
            "incidents:read",
            "knowledge:read",
        }
    )
    return {
        "employee": read_permissions,
        "it_support": read_permissions,
        "knowledge_maintainer": read_permissions,
        "project_maintainer": read_permissions,
    }


def _register(
    registry: ToolRegistry,
    *,
    name: str,
    description: str,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
    permission: str,
    adapter: Any,
) -> None:
    async def async_adapter(value: BaseModel, context: ToolExecutionContext) -> Any:
        return adapter(value, context)

    registry.register(
        ToolDefinition(
            name=name,
            version="1.0.0",
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            required_permissions=frozenset({permission}),
            risk_level=ToolRiskLevel.R0,
            has_side_effect=False,
            timeout_seconds=1.0,
            retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
        ),
        async_adapter,
    )


def _value(model: BaseModel, **changes: Any) -> dict[str, Any]:
    return model.model_copy(update=changes).model_dump(mode="json")
