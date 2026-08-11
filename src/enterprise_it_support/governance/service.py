"""Application service for deterministic policy and local human approval."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from enterprise_it_support.governance.domain import (
    FINANCE_ADMIN_ACTION,
    FINANCE_ADMIN_TARGET,
    FINANCE_ADMIN_TOOL,
    ApprovalDecisionValue,
    GovernanceAccessDeniedError,
    LocalUserNotFoundError,
    PolicyDecision,
    PolicyInput,
    RiskLevel,
    StoredApprovalRequest,
)
from enterprise_it_support.governance.persistence import GovernanceRepository
from enterprise_it_support.governance.policy import PolicyEngine
from enterprise_it_support.service_desk.domain import AuditEventCreate
from enterprise_it_support.service_desk.domain import PolicyDecision as AuditPolicyDecision
from enterprise_it_support.service_desk.persistence import AuditEventRepository


class GovernanceService:
    """Coordinate local identity, deterministic policy, approval, and audit."""

    def __init__(
        self,
        *,
        repository: GovernanceRepository,
        policy_engine: PolicyEngine,
        audit_events: AuditEventRepository,
    ) -> None:
        self._repository = repository
        self._policy_engine = policy_engine
        self._audit_events = audit_events

    @asynccontextmanager
    async def decision_lock(self, approval_request_id: UUID) -> AsyncIterator[None]:
        async with self._repository.decision_lock(approval_request_id):
            yield

    async def evaluate_finance_admin_request(
        self,
        *,
        actor_id: str,
        role: str,
        business_justification: str | None,
        request_id: str,
    ) -> PolicyDecision:
        try:
            user = await self._repository.get_user(actor_id)
        except LocalUserNotFoundError:
            await self._audit_policy(
                actor_id=actor_id,
                decision=PolicyDecision.DENY,
                request_id=request_id,
                business_justification=business_justification,
            )
            raise
        decision = self._policy_engine.evaluate(
            PolicyInput(
                user=user,
                role=role,
                action=FINANCE_ADMIN_ACTION,
                tool=FINANCE_ADMIN_TOOL,
                target_resource=FINANCE_ADMIN_TARGET,
                risk_level=RiskLevel.R3,
                request_context={
                    "business_justification": business_justification or "",
                },
            )
        )
        if decision is not PolicyDecision.REQUIRE_APPROVAL:
            await self._audit_policy(
                actor_id=actor_id,
                decision=decision,
                request_id=request_id,
                business_justification=business_justification,
            )
        return decision

    async def create_finance_admin_approval(
        self,
        *,
        actor_id: str,
        role: str,
        business_justification: str,
        idempotency_key: str,
        source_agent_run_id: UUID,
        request_id: str,
    ) -> StoredApprovalRequest:
        user = await self._repository.get_user(actor_id)
        decision = self._policy_engine.evaluate(
            PolicyInput(
                user=user,
                role=role,
                action=FINANCE_ADMIN_ACTION,
                tool=FINANCE_ADMIN_TOOL,
                target_resource=FINANCE_ADMIN_TARGET,
                risk_level=RiskLevel.R3,
                request_context={"business_justification": business_justification},
            )
        )
        if decision is not PolicyDecision.REQUIRE_APPROVAL:
            raise PermissionError(f"Policy returned {decision.value}")
        return await self._repository.create_approval(
            requester=user,
            action=FINANCE_ADMIN_ACTION,
            tool=FINANCE_ADMIN_TOOL,
            target_resource=FINANCE_ADMIN_TARGET,
            business_justification=business_justification,
            request_context={"requested_role": role},
            idempotency_key=idempotency_key,
            source_agent_run_id=source_agent_run_id,
            request_id=request_id,
        )

    async def list_pending(
        self,
        *,
        actor_id: str,
        limit: int,
        offset: int,
        request_id: str,
    ) -> tuple[StoredApprovalRequest, ...]:
        try:
            return await self._repository.list_pending(
                actor_external_id=actor_id,
                limit=limit,
                offset=offset,
            )
        except (GovernanceAccessDeniedError, LocalUserNotFoundError):
            await self._audit_access_denial(
                actor_id=actor_id,
                action="list_pending_approvals",
                target="approval_queue",
                request_id=request_id,
                parameters_summary={},
            )
            raise

    async def decide(
        self,
        *,
        approval_request_id: UUID,
        actor_id: str,
        decision: ApprovalDecisionValue,
        rationale: str | None,
        request_id: str,
    ) -> StoredApprovalRequest:
        try:
            return await self._repository.decide(
                approval_request_id=approval_request_id,
                actor_external_id=actor_id,
                decision=decision,
                rationale=rationale,
                request_id=request_id,
            )
        except (GovernanceAccessDeniedError, LocalUserNotFoundError):
            await self._audit_access_denial(
                actor_id=actor_id,
                action=f"{decision.value}_approval",
                target=f"approval_request:{approval_request_id}",
                request_id=request_id,
                parameters_summary={"rationale_length": len(rationale or "")},
            )
            raise

    async def mark_resumed(
        self,
        *,
        approval_request_id: UUID,
        decision: ApprovalDecisionValue,
        request_id: str,
    ) -> StoredApprovalRequest:
        return await self._repository.mark_resumed(
            approval_request_id=approval_request_id,
            decision=decision,
            request_id=request_id,
        )

    async def audit_resume_failure(
        self,
        *,
        approval_request_id: UUID,
        source_agent_run_id: UUID,
        decision: ApprovalDecisionValue,
        request_id: str,
    ) -> None:
        await self._audit_events.append(
            AuditEventCreate(
                actor="enterprise-it-support-agent",
                action="resume_approval_run",
                target=f"agent_run:{source_agent_run_id}",
                parameters_summary={
                    "approval_request_id": str(approval_request_id),
                    "decision": decision.value,
                },
                policy_decision=AuditPolicyDecision.ALLOW,
                execution_result="failed:runtime_unavailable",
                request_id=request_id,
            )
        )

    async def complete_simulated_execution(
        self,
        *,
        approval_request_id: UUID,
        request_id: str,
    ) -> StoredApprovalRequest:
        return await self._repository.mark_executed(
            approval_request_id=approval_request_id,
            simulated_result={
                "status": "simulated_success",
                "message": "模拟执行成功; 未修改任何真实权限系统。",
                "external_system_modified": False,
            },
            request_id=request_id,
        )

    async def get(self, approval_request_id: UUID) -> StoredApprovalRequest:
        return await self._repository.get(approval_request_id)

    async def _audit_policy(
        self,
        *,
        actor_id: str,
        decision: PolicyDecision,
        request_id: str,
        business_justification: str | None,
    ) -> None:
        await self._audit_events.append(
            AuditEventCreate(
                actor=actor_id,
                action=FINANCE_ADMIN_ACTION,
                target=FINANCE_ADMIN_TARGET,
                parameters_summary={
                    "business_justification_length": len((business_justification or "").strip()),
                    "risk_level": RiskLevel.R3.value,
                },
                policy_decision=AuditPolicyDecision(decision.value),
                execution_result="not_executed",
                request_id=request_id,
            )
        )

    async def _audit_access_denial(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        request_id: str,
        parameters_summary: dict[str, object],
    ) -> None:
        await self._audit_events.append(
            AuditEventCreate(
                actor=actor_id,
                action=action,
                target=target,
                parameters_summary=parameters_summary,
                policy_decision=AuditPolicyDecision.DENY,
                execution_result="not_executed:access_denied",
                request_id=request_id,
            )
        )
