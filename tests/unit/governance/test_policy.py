"""Deterministic Policy Engine behavior."""

from uuid import uuid4

import pytest

from enterprise_it_support.governance.domain import (
    FINANCE_ADMIN_ACTION,
    FINANCE_ADMIN_REQUEST_PERMISSION,
    FINANCE_ADMIN_TARGET,
    FINANCE_ADMIN_TOOL,
    PolicyDecision,
    PolicyInput,
    RiskLevel,
    StoredUser,
)
from enterprise_it_support.governance.policy import PolicyEngine


def _request(
    risk_level: RiskLevel,
    *,
    role: str = "employee",
    justification: str = "Quarter-end finance platform support",
    active: bool = True,
    permissions: frozenset[str] | None = None,
) -> PolicyInput:
    return PolicyInput(
        user=StoredUser(
            id=uuid4(),
            external_id="employee-demo",
            display_name="Employee Demo",
            is_active=active,
            roles=frozenset({"employee"}),
            permissions=(
                frozenset({FINANCE_ADMIN_REQUEST_PERMISSION})
                if permissions is None
                else permissions
            ),
        ),
        role=role,
        action=FINANCE_ADMIN_ACTION,
        tool=FINANCE_ADMIN_TOOL,
        target_resource=FINANCE_ADMIN_TARGET,
        risk_level=risk_level,
        request_context={"business_justification": justification},
    )


@pytest.mark.parametrize(
    ("risk_level", "expected"),
    [
        (RiskLevel.R0, PolicyDecision.ALLOW),
        (RiskLevel.R1, PolicyDecision.REQUIRE_CONFIRMATION),
        (RiskLevel.R2, PolicyDecision.REQUIRE_CONFIRMATION),
        (RiskLevel.R3, PolicyDecision.REQUIRE_APPROVAL),
        (RiskLevel.R4, PolicyDecision.DENY),
    ],
)
def test_policy_engine_returns_only_risk_owned_decisions(
    risk_level: RiskLevel,
    expected: PolicyDecision,
) -> None:
    assert PolicyEngine().evaluate(_request(risk_level)) is expected


def test_r3_requires_business_justification_before_approval() -> None:
    decision = PolicyEngine().evaluate(_request(RiskLevel.R3, justification=" "))

    assert decision is PolicyDecision.NEED_MORE_CONTEXT


@pytest.mark.parametrize(
    "policy_input",
    [
        _request(RiskLevel.R3, role="admin"),
        _request(RiskLevel.R3, active=False),
        _request(RiskLevel.R3, permissions=frozenset()),
    ],
)
def test_policy_denies_unassigned_role_inactive_user_and_missing_permission(
    policy_input: PolicyInput,
) -> None:
    assert PolicyEngine().evaluate(policy_input) is PolicyDecision.DENY


def test_r4_is_denied_even_with_approver_like_permissions() -> None:
    request = _request(
        RiskLevel.R4,
        permissions=frozenset(
            {
                FINANCE_ADMIN_REQUEST_PERMISSION,
                "approval:read",
                "approval:decide",
            }
        ),
    )

    assert PolicyEngine().evaluate(request) is PolicyDecision.DENY
