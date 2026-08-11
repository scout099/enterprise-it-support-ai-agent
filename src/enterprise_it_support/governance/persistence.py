"""Transactional PostgreSQL persistence for RBAC identities and approvals."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.governance.domain import (
    APPROVAL_DECIDE_PERMISSION,
    APPROVAL_READ_PERMISSION,
    ApprovalAlreadyDecidedError,
    ApprovalConflictError,
    ApprovalDecisionValue,
    ApprovalRequestNotFoundError,
    ApprovalStatus,
    GovernanceAccessDeniedError,
    LocalUserNotFoundError,
    PolicyDecision,
    RiskLevel,
    StoredApprovalDecision,
    StoredApprovalRequest,
    StoredUser,
)
from enterprise_it_support.governance.models import (
    ApprovalDecision,
    ApprovalRequest,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from enterprise_it_support.service_desk.models import AuditEvent


class GovernanceRepository:
    """Resolve local identities and enforce approval transitions under row locks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def decision_lock(self, approval_request_id: UUID) -> AsyncIterator[None]:
        """Serialize decision/resume attempts and release automatically on process loss."""
        lock_key = int.from_bytes(approval_request_id.bytes[:8], signed=True)
        async with self._session_factory() as session, session.begin():
            await session.execute(select(func.pg_advisory_xact_lock(lock_key)))
            yield

    async def get_user(self, external_id: str) -> StoredUser:
        async with self._session_factory() as session:
            return await self._get_user(session, external_id)

    async def create_approval(
        self,
        *,
        requester: StoredUser,
        action: str,
        tool: str,
        target_resource: str,
        business_justification: str,
        request_context: dict[str, object],
        idempotency_key: str,
        source_agent_run_id: UUID,
        request_id: str,
    ) -> StoredApprovalRequest:
        async with self._session_factory() as session, session.begin():
            existing = await session.scalar(
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.requester_user_id == requester.id,
                    ApprovalRequest.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                self._ensure_same_request(
                    existing,
                    action=action,
                    tool=tool,
                    target_resource=target_resource,
                    business_justification=business_justification,
                    source_agent_run_id=source_agent_run_id,
                )
                return await self._stored_request(session, existing)
            existing_run = await session.scalar(
                select(ApprovalRequest).where(
                    ApprovalRequest.source_agent_run_id == source_agent_run_id
                )
            )
            if existing_run is not None:
                self._ensure_same_request(
                    existing_run,
                    action=action,
                    tool=tool,
                    target_resource=target_resource,
                    business_justification=business_justification,
                    source_agent_run_id=source_agent_run_id,
                )
                return await self._stored_request(session, existing_run)
            row = ApprovalRequest(
                requester_user_id=requester.id,
                action=action,
                tool=tool,
                target_resource=target_resource,
                risk_level=RiskLevel.R3.value,
                business_justification=business_justification,
                request_context=request_context,
                policy_decision=PolicyDecision.REQUIRE_APPROVAL.value,
                status=ApprovalStatus.PENDING.value,
                idempotency_key=idempotency_key,
                source_agent_run_id=source_agent_run_id,
                checkpoint_node="await_human_approval",
            )
            session.add(row)
            await session.flush()
            session.add(
                AuditEvent(
                    actor=requester.external_id,
                    action=action,
                    target=target_resource,
                    parameters_summary={
                        "approval_request_id": str(row.id),
                        "business_justification_length": len(business_justification),
                        "risk_level": RiskLevel.R3.value,
                    },
                    policy_decision=PolicyDecision.REQUIRE_APPROVAL.value,
                    execution_result="pending_human_approval",
                    request_id=request_id,
                )
            )
            await session.flush()
            return await self._stored_request(session, row)

    async def list_pending(
        self,
        *,
        actor_external_id: str,
        limit: int,
        offset: int,
    ) -> tuple[StoredApprovalRequest, ...]:
        async with self._session_factory() as session:
            actor = await self._get_user(session, actor_external_id)
            self._require_permission(actor, APPROVAL_READ_PERMISSION)
            rows = (
                await session.scalars(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.status == ApprovalStatus.PENDING.value)
                    .order_by(ApprovalRequest.created_at, ApprovalRequest.id)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
            return tuple([await self._stored_request(session, row) for row in rows])

    async def decide(
        self,
        *,
        approval_request_id: UUID,
        actor_external_id: str,
        decision: ApprovalDecisionValue,
        rationale: str | None,
        request_id: str,
    ) -> StoredApprovalRequest:
        async with self._session_factory() as session, session.begin():
            actor = await self._get_user(session, actor_external_id)
            self._require_permission(actor, APPROVAL_DECIDE_PERMISSION)
            row = await session.scalar(
                select(ApprovalRequest)
                .where(ApprovalRequest.id == approval_request_id)
                .with_for_update()
            )
            if row is None:
                raise ApprovalRequestNotFoundError(str(approval_request_id))
            if row.requester_user_id == actor.id:
                raise GovernanceAccessDeniedError("Requesters cannot approve their own request")
            if row.status != ApprovalStatus.PENDING.value:
                decision_row = await session.scalar(
                    select(ApprovalDecision).where(ApprovalDecision.approval_request_id == row.id)
                )
                if not self._is_recoverable_decision(
                    row,
                    decision_row=decision_row,
                    actor=actor,
                    decision=decision,
                    rationale=rationale,
                ):
                    raise ApprovalAlreadyDecidedError(str(approval_request_id))
                return await self._stored_request(session, row)
            decided_at = datetime.now(UTC)
            session.add(
                ApprovalDecision(
                    approval_request_id=row.id,
                    approver_user_id=actor.id,
                    decision=decision.value,
                    rationale=rationale,
                    decided_at=decided_at,
                )
            )
            row.status = (
                ApprovalStatus.APPROVED.value
                if decision is ApprovalDecisionValue.APPROVE
                else ApprovalStatus.REJECTED.value
            )
            row.decided_at = decided_at
            session.add(
                AuditEvent(
                    actor=actor.external_id,
                    action=f"{decision.value}_approval",
                    target=f"approval_request:{row.id}",
                    parameters_summary={
                        "source_agent_run_id": str(row.source_agent_run_id),
                        "rationale_length": len(rationale or ""),
                    },
                    policy_decision=(
                        PolicyDecision.ALLOW.value
                        if decision is ApprovalDecisionValue.APPROVE
                        else PolicyDecision.DENY.value
                    ),
                    execution_result=row.status,
                    request_id=request_id,
                )
            )
            await session.flush()
            return await self._stored_request(session, row)

    async def mark_resumed(
        self,
        *,
        approval_request_id: UUID,
        decision: ApprovalDecisionValue,
        request_id: str,
    ) -> StoredApprovalRequest:
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(ApprovalRequest)
                .where(ApprovalRequest.id == approval_request_id)
                .with_for_update()
            )
            if row is None:
                raise ApprovalRequestNotFoundError(str(approval_request_id))
            if row.resumed_at is not None:
                return await self._stored_request(session, row)
            decision_row = await session.scalar(
                select(ApprovalDecision).where(ApprovalDecision.approval_request_id == row.id)
            )
            expected_statuses = (
                {ApprovalStatus.APPROVED.value, ApprovalStatus.EXECUTED.value}
                if decision is ApprovalDecisionValue.APPROVE
                else {ApprovalStatus.REJECTED.value}
            )
            if (
                decision_row is None
                or decision_row.decision != decision.value
                or row.status not in expected_statuses
            ):
                raise ApprovalConflictError("Approval resume does not match the saved decision")
            row.resumed_at = datetime.now(UTC)
            session.add(
                AuditEvent(
                    actor="enterprise-it-support-agent",
                    action="resume_approval_run",
                    target=f"agent_run:{row.source_agent_run_id}",
                    parameters_summary={
                        "approval_request_id": str(row.id),
                        "decision": decision.value,
                    },
                    policy_decision=PolicyDecision.ALLOW.value,
                    execution_result=f"completed:{decision.value}",
                    request_id=request_id,
                )
            )
            await session.flush()
            return await self._stored_request(session, row)

    async def mark_executed(
        self,
        *,
        approval_request_id: UUID,
        simulated_result: dict[str, object],
        request_id: str,
    ) -> StoredApprovalRequest:
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(ApprovalRequest)
                .where(ApprovalRequest.id == approval_request_id)
                .with_for_update()
            )
            if row is None:
                raise ApprovalRequestNotFoundError(str(approval_request_id))
            if row.status == ApprovalStatus.EXECUTED.value:
                return await self._stored_request(session, row)
            if row.status != ApprovalStatus.APPROVED.value:
                raise ApprovalConflictError("Only an approved request can be simulated")
            row.status = ApprovalStatus.EXECUTED.value
            row.simulated_result = simulated_result
            row.executed_at = datetime.now(UTC)
            session.add(
                AuditEvent(
                    actor="enterprise-it-support-agent",
                    action=row.action,
                    target=row.target_resource,
                    parameters_summary={
                        "approval_request_id": str(row.id),
                        "simulation": True,
                    },
                    policy_decision=PolicyDecision.ALLOW.value,
                    execution_result="simulated_success",
                    request_id=request_id,
                )
            )
            await session.flush()
            return await self._stored_request(session, row)

    async def get(self, approval_request_id: UUID) -> StoredApprovalRequest:
        async with self._session_factory() as session:
            row = await session.get(ApprovalRequest, approval_request_id)
            if row is None:
                raise ApprovalRequestNotFoundError(str(approval_request_id))
            return await self._stored_request(session, row)

    @staticmethod
    def _require_permission(user: StoredUser, permission: str) -> None:
        if not user.is_active or permission not in user.permissions:
            raise GovernanceAccessDeniedError(permission)

    @staticmethod
    def _ensure_same_request(
        row: ApprovalRequest,
        *,
        action: str,
        tool: str,
        target_resource: str,
        business_justification: str,
        source_agent_run_id: UUID,
    ) -> None:
        if (
            row.action != action
            or row.tool != tool
            or row.target_resource != target_resource
            or row.business_justification != business_justification
            or row.source_agent_run_id != source_agent_run_id
        ):
            raise ApprovalConflictError("Approval idempotency key conflicts with another request")

    @staticmethod
    def _is_recoverable_decision(
        row: ApprovalRequest,
        *,
        decision_row: ApprovalDecision | None,
        actor: StoredUser,
        decision: ApprovalDecisionValue,
        rationale: str | None,
    ) -> bool:
        expected_statuses = (
            {ApprovalStatus.APPROVED.value, ApprovalStatus.EXECUTED.value}
            if decision is ApprovalDecisionValue.APPROVE
            else {ApprovalStatus.REJECTED.value}
        )
        return bool(
            row.resumed_at is None
            and row.status in expected_statuses
            and decision_row is not None
            and decision_row.approver_user_id == actor.id
            and decision_row.decision == decision.value
            and decision_row.rationale == rationale
        )

    async def _get_user(self, session: AsyncSession, external_id: str) -> StoredUser:
        user = await session.scalar(select(User).where(User.external_id == external_id))
        if user is None:
            raise LocalUserNotFoundError(external_id)
        roles = frozenset(
            (
                await session.scalars(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user.id)
                )
            ).all()
        )
        permissions = frozenset(
            (
                await session.scalars(
                    select(Permission.name)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .join(UserRole, UserRole.role_id == RolePermission.role_id)
                    .where(UserRole.user_id == user.id)
                )
            ).all()
        )
        return StoredUser(
            id=user.id,
            external_id=user.external_id,
            display_name=user.display_name,
            is_active=user.is_active,
            roles=roles,
            permissions=permissions,
        )

    async def _stored_request(
        self,
        session: AsyncSession,
        row: ApprovalRequest,
    ) -> StoredApprovalRequest:
        requester_external_id = await session.scalar(
            select(User.external_id).where(User.id == row.requester_user_id)
        )
        decision_row = await session.scalar(
            select(ApprovalDecision).where(ApprovalDecision.approval_request_id == row.id)
        )
        decision = None
        if decision_row is not None:
            approver_external_id = await session.scalar(
                select(User.external_id).where(User.id == decision_row.approver_user_id)
            )
            decision = StoredApprovalDecision(
                id=decision_row.id,
                approval_request_id=decision_row.approval_request_id,
                approver_user_id=decision_row.approver_user_id,
                approver_external_id=str(approver_external_id),
                decision=ApprovalDecisionValue(decision_row.decision),
                rationale=decision_row.rationale,
                decided_at=decision_row.decided_at,
            )
        return StoredApprovalRequest(
            id=row.id,
            requester_user_id=row.requester_user_id,
            requester_external_id=str(requester_external_id),
            action=row.action,
            tool=row.tool,
            target_resource=row.target_resource,
            risk_level=RiskLevel(row.risk_level),
            business_justification=row.business_justification,
            request_context=row.request_context,
            policy_decision=PolicyDecision(row.policy_decision),
            status=ApprovalStatus(row.status),
            idempotency_key=row.idempotency_key,
            source_agent_run_id=row.source_agent_run_id,
            checkpoint_node=row.checkpoint_node,
            simulated_result=row.simulated_result,
            created_at=row.created_at,
            decided_at=row.decided_at,
            executed_at=row.executed_at,
            resumed_at=row.resumed_at,
            decision=decision,
        )
