"""Pure deterministic policy decisions for enterprise support actions."""

from enterprise_it_support.governance.domain import (
    FINANCE_ADMIN_ACTION,
    FINANCE_ADMIN_REQUEST_PERMISSION,
    FINANCE_ADMIN_TARGET,
    FINANCE_ADMIN_TOOL,
    PolicyDecision,
    PolicyInput,
    RiskLevel,
)


class PolicyEngine:
    """Return one allowlisted decision without consulting a model."""

    def evaluate(self, request: PolicyInput) -> PolicyDecision:
        role = request.role.strip()
        if not request.user.is_active or role not in request.user.roles:
            return PolicyDecision.DENY
        if request.risk_level is RiskLevel.R4:
            return PolicyDecision.DENY
        if not all(
            value.strip() for value in (request.action, request.tool, request.target_resource)
        ):
            return PolicyDecision.NEED_MORE_CONTEXT
        if not self._is_known_action(request):
            return PolicyDecision.DENY
        if FINANCE_ADMIN_REQUEST_PERMISSION not in request.user.permissions:
            return PolicyDecision.DENY
        justification = str(request.request_context.get("business_justification", "")).strip()
        if request.risk_level in {RiskLevel.R2, RiskLevel.R3} and not justification:
            return PolicyDecision.NEED_MORE_CONTEXT
        return {
            RiskLevel.R0: PolicyDecision.ALLOW,
            RiskLevel.R1: PolicyDecision.REQUIRE_CONFIRMATION,
            RiskLevel.R2: PolicyDecision.REQUIRE_CONFIRMATION,
            RiskLevel.R3: PolicyDecision.REQUIRE_APPROVAL,
            RiskLevel.R4: PolicyDecision.DENY,
        }[request.risk_level]

    @staticmethod
    def _is_known_action(request: PolicyInput) -> bool:
        return (
            request.action == FINANCE_ADMIN_ACTION
            and request.tool == FINANCE_ADMIN_TOOL
            and request.target_resource == FINANCE_ADMIN_TARGET
        )
