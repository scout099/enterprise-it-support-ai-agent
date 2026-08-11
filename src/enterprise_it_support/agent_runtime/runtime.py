"""Bounded LangGraph orchestration for Phase 6 intent routing."""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from enterprise_it_support.agent_runtime.persistence import (
    AgentRunStore,
    StoredAgentRun,
)
from enterprise_it_support.agent_runtime.rag import RAGAnswerService
from enterprise_it_support.agent_runtime.state import (
    INTENT_PROMPT_VERSION,
    INTENT_SYSTEM_PROMPT,
    AgentIntent,
    AgentRunStatus,
    AgentState,
    AgentStepStatus,
    IntentClassification,
    RiskLevel,
    initial_agent_state,
)
from enterprise_it_support.governance.domain import (
    FINANCE_ADMIN_ACTION,
    FINANCE_ADMIN_TARGET,
    FINANCE_ADMIN_TOOL,
    ApprovalDecisionValue,
    LocalUserNotFoundError,
    PolicyDecision,
)
from enterprise_it_support.governance.service import GovernanceService
from enterprise_it_support.intelligence.model_gateway import (
    ModelGateway,
    ModelMessage,
)
from enterprise_it_support.knowledge.retrieval import (
    Citation,
    KnowledgeRetriever,
    RetrievalMethod,
    SearchFilters,
    SearchResult,
    UserContext,
)
from enterprise_it_support.tools.contracts import (
    ToolExecutionContext,
    ToolExecutionRequest,
)
from enterprise_it_support.tools.gateway import (
    ToolAuditUnavailableError,
    ToolExecutionGateway,
)

Node = Callable[[AgentState], Awaitable[dict[str, Any]]]
logger = logging.getLogger(__name__)


class AgentNodeLimitError(RuntimeError):
    """Raised when graph node attempts exhaust the configured hard budget."""


@dataclass(frozen=True)
class AgentRuntimeLimits:
    """All graph bounds are explicit and validated before compilation."""

    confidence_threshold: float
    max_nodes: int
    max_retries: int
    max_tool_calls: int
    node_timeout_seconds: float
    total_timeout_seconds: float

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("Intent confidence threshold must be between zero and one")
        if self.max_nodes < 4:
            raise ValueError("Agent maximum nodes must be at least four")
        if self.max_retries < 0:
            raise ValueError("Agent maximum retries cannot be negative")
        if not 1 <= self.max_tool_calls <= 20:
            raise ValueError("Agent maximum tool calls must be between one and twenty")
        if self.node_timeout_seconds <= 0:
            raise ValueError("Agent node timeout must be positive")
        if self.total_timeout_seconds <= self.node_timeout_seconds:
            raise ValueError("Agent total timeout must exceed node timeout")


class AgentRuntime:
    """Execute one recoverable, auditable, read-only support graph."""

    def __init__(
        self,
        *,
        model_gateway: ModelGateway,
        retriever: KnowledgeRetriever,
        rag_answer_service: RAGAnswerService,
        tool_gateway: ToolExecutionGateway,
        run_store: AgentRunStore,
        checkpointer: BaseCheckpointSaver[Any],
        limits: AgentRuntimeLimits,
        top_k: int,
        governance_service: GovernanceService | None = None,
    ) -> None:
        if top_k < 1:
            raise ValueError("Agent retrieval top_k must be positive")
        self._model_gateway = model_gateway
        self._retriever = retriever
        self._rag_answer_service = rag_answer_service
        self._tool_gateway = tool_gateway
        self._run_store = run_store
        self._limits = limits
        self._top_k = top_k
        self._governance_service = governance_service
        self._graph = self._build_graph(checkpointer)

    async def run(
        self,
        *,
        user_message: str,
        user_role: str,
        request_id: str,
        conversation_id: UUID | None = None,
        actor_id: str | None = None,
        idempotency_key: str | None = None,
        business_justification: str | None = None,
    ) -> StoredAgentRun:
        """Create and execute one graph run within total-time and recursion limits."""
        run_id = uuid4()
        state = initial_agent_state(
            run_id=str(run_id),
            request_id=request_id,
            conversation_id=None if conversation_id is None else str(conversation_id),
            user_message=user_message,
            user_role=user_role,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            business_justification=business_justification,
        )
        await self._run_store.create_run(state)
        config = self._config(run_id)
        try:
            async with asyncio.timeout(self._limits.total_timeout_seconds):
                result = await self._graph.ainvoke(state, config=config)
        except TimeoutError:
            await self._record_runtime_failure(run_id, "agent_timeout")
        except (AgentNodeLimitError, GraphRecursionError):
            await self._record_runtime_failure(run_id, "max_nodes_exceeded")
        else:
            await self._run_store.update_run(_state_from_graph_values(result))
        return await self._run_store.get(run_id)

    async def load_checkpoint(self, run_id: UUID) -> AgentState | None:
        """Recover the latest LangGraph state for an Agent Run."""
        snapshot = await self._graph.aget_state(self._config(run_id))
        if not snapshot.values:
            return None
        return _state_from_graph_values(snapshot.values)

    async def resume(
        self,
        run_id: UUID,
        *,
        resume_value: dict[str, Any] | None = None,
    ) -> StoredAgentRun:
        """Continue a checkpoint that still has pending graph nodes."""
        snapshot = await self._graph.aget_state(self._config(run_id))
        if not snapshot.values:
            return await self._run_store.get(run_id)
        if not snapshot.next:
            return await self._run_store.get(run_id)
        try:
            async with asyncio.timeout(self._limits.total_timeout_seconds):
                graph_input = None if resume_value is None else Command(resume=resume_value)
                result = await self._graph.ainvoke(
                    graph_input,
                    config=self._config(run_id),
                )
        except TimeoutError:
            await self._record_runtime_failure(run_id, "agent_timeout")
        except (AgentNodeLimitError, GraphRecursionError):
            await self._record_runtime_failure(run_id, "max_nodes_exceeded")
        else:
            await self._run_store.update_run(_state_from_graph_values(result))
        return await self._run_store.get(run_id)

    def _build_graph(self, checkpointer: BaseCheckpointSaver[Any]) -> Any:
        builder = StateGraph(AgentState)
        builder.add_node("intake", self._bounded_node("intake", self._intake))
        builder.add_node(
            "classify_intent",
            self._bounded_node("classify_intent", self._classify_intent, retryable=True),
        )
        builder.add_node(
            "evaluate_governance_policy",
            self._bounded_node(
                "evaluate_governance_policy",
                self._evaluate_governance_policy,
            ),
        )
        builder.add_node(
            "create_approval_request",
            self._bounded_node(
                "create_approval_request",
                self._create_approval_request,
            ),
        )
        builder.add_node(
            "await_human_approval",
            self._bounded_node(
                "await_human_approval",
                self._await_human_approval,
            ),
        )
        builder.add_node(
            "simulate_approved_action",
            self._bounded_node(
                "simulate_approved_action",
                self._simulate_approved_action,
            ),
        )
        builder.add_node(
            "finish_rejected_action",
            self._bounded_node(
                "finish_rejected_action",
                self._finish_rejected_action,
            ),
        )
        builder.add_node(
            "request_clarification",
            self._bounded_node("request_clarification", self._request_clarification),
        )
        builder.add_node(
            "retrieve_knowledge",
            self._bounded_node("retrieve_knowledge", self._retrieve_knowledge, retryable=True),
        )
        builder.add_node(
            "compose_answer",
            self._bounded_node("compose_answer", self._compose_answer),
        )
        builder.add_node(
            "vpn_diagnosis",
            self._bounded_node("vpn_diagnosis", self._vpn_diagnosis),
        )
        builder.add_node(
            "vpn_check_network",
            self._bounded_node("vpn_check_network", self._vpn_check_network),
        )
        builder.add_node(
            "vpn_check_client",
            self._bounded_node("vpn_check_client", self._vpn_check_client),
        )
        builder.add_node(
            "vpn_check_service",
            self._bounded_node("vpn_check_service", self._vpn_check_service),
        )
        builder.add_node(
            "vpn_check_incidents",
            self._bounded_node("vpn_check_incidents", self._vpn_check_incidents),
        )
        builder.add_node(
            "vpn_search_knowledge",
            self._bounded_node("vpn_search_knowledge", self._vpn_search_knowledge),
        )
        builder.add_node(
            "vpn_complete",
            self._bounded_node("vpn_complete", self._vpn_complete),
        )
        builder.add_node(
            "outlook_diagnosis",
            self._bounded_node("outlook_diagnosis", self._outlook_diagnosis),
        )
        builder.add_node(
            "outlook_check_service",
            self._bounded_node("outlook_check_service", self._outlook_check_service),
        )
        builder.add_node(
            "outlook_check_account",
            self._bounded_node("outlook_check_account", self._outlook_check_account),
        )
        builder.add_node(
            "outlook_check_incidents",
            self._bounded_node("outlook_check_incidents", self._outlook_check_incidents),
        )
        builder.add_node(
            "outlook_search_knowledge",
            self._bounded_node("outlook_search_knowledge", self._outlook_search_knowledge),
        )
        builder.add_node(
            "outlook_complete",
            self._bounded_node("outlook_complete", self._outlook_complete),
        )
        builder.add_node(
            "account_diagnosis",
            self._bounded_node("account_diagnosis", self._account_diagnosis),
        )
        builder.add_node(
            "account_check_incidents",
            self._bounded_node("account_check_incidents", self._account_check_incidents),
        )
        builder.add_node(
            "account_search_knowledge",
            self._bounded_node("account_search_knowledge", self._account_search_knowledge),
        )
        builder.add_node(
            "account_complete",
            self._bounded_node("account_complete", self._account_complete),
        )
        builder.add_node(
            "ticket_unavailable",
            self._bounded_node("ticket_unavailable", self._ticket_unavailable),
        )
        builder.add_node(
            "escalate_to_human",
            self._bounded_node("escalate_to_human", self._escalate_to_human),
        )
        builder.add_node("finalize", self._bounded_node("finalize", self._finalize))

        builder.add_edge(START, "intake")
        builder.add_conditional_edges(
            "intake",
            self._route_after_intake,
            {
                "classify_intent": "classify_intent",
                "evaluate_governance_policy": "evaluate_governance_policy",
                "finalize": "finalize",
            },
        )
        builder.add_conditional_edges(
            "evaluate_governance_policy",
            self._route_after_governance_policy,
            {
                "create_approval_request": "create_approval_request",
                "finalize": "finalize",
            },
        )
        builder.add_edge("create_approval_request", "await_human_approval")
        builder.add_conditional_edges(
            "await_human_approval",
            self._route_after_human_approval,
            {
                "simulate_approved_action": "simulate_approved_action",
                "finish_rejected_action": "finish_rejected_action",
            },
        )
        builder.add_edge("simulate_approved_action", "finalize")
        builder.add_edge("finish_rejected_action", "finalize")
        builder.add_conditional_edges(
            "classify_intent",
            self._route_after_classification,
            {
                "request_clarification": "request_clarification",
                "retrieve_knowledge": "retrieve_knowledge",
                "vpn_diagnosis": "vpn_diagnosis",
                "outlook_diagnosis": "outlook_diagnosis",
                "account_diagnosis": "account_diagnosis",
                "ticket_unavailable": "ticket_unavailable",
                "escalate_to_human": "escalate_to_human",
                "finalize": "finalize",
            },
        )
        builder.add_conditional_edges(
            "retrieve_knowledge",
            self._route_after_retrieval,
            {"compose_answer": "compose_answer", "finalize": "finalize"},
        )
        diagnostic_edges = (
            ("vpn_diagnosis", "vpn_check_network"),
            ("vpn_check_network", "vpn_check_client"),
            ("vpn_check_client", "vpn_check_service"),
            ("vpn_check_service", "vpn_check_incidents"),
            ("outlook_diagnosis", "outlook_check_service"),
            ("outlook_check_service", "outlook_check_account"),
            ("outlook_check_account", "outlook_check_incidents"),
            ("account_diagnosis", "account_check_incidents"),
        )
        for source, destination in diagnostic_edges:
            builder.add_conditional_edges(
                source,
                _diagnostic_route(destination),
                {
                    destination: destination,
                    "escalate_to_human": "escalate_to_human",
                },
            )
        builder.add_conditional_edges(
            "vpn_check_incidents",
            self._route_vpn_after_incidents,
            {
                "vpn_search_knowledge": "vpn_search_knowledge",
                "escalate_to_human": "escalate_to_human",
            },
        )
        builder.add_conditional_edges(
            "vpn_search_knowledge",
            _diagnostic_route("vpn_complete"),
            {
                "vpn_complete": "vpn_complete",
                "escalate_to_human": "escalate_to_human",
            },
        )
        builder.add_conditional_edges(
            "outlook_check_incidents",
            self._route_outlook_after_incidents,
            {
                "outlook_search_knowledge": "outlook_search_knowledge",
                "escalate_to_human": "escalate_to_human",
            },
        )
        builder.add_conditional_edges(
            "outlook_search_knowledge",
            _diagnostic_route("outlook_complete"),
            {
                "outlook_complete": "outlook_complete",
                "escalate_to_human": "escalate_to_human",
            },
        )
        builder.add_conditional_edges(
            "account_search_knowledge",
            _diagnostic_route("account_complete"),
            {
                "account_complete": "account_complete",
                "escalate_to_human": "escalate_to_human",
            },
        )
        builder.add_conditional_edges(
            "account_check_incidents",
            self._route_account_after_incidents,
            {
                "account_search_knowledge": "account_search_knowledge",
                "escalate_to_human": "escalate_to_human",
            },
        )
        for node_name in (
            "request_clarification",
            "compose_answer",
            "vpn_complete",
            "outlook_complete",
            "account_complete",
            "ticket_unavailable",
            "escalate_to_human",
        ):
            builder.add_edge(node_name, "finalize")
        builder.add_edge("finalize", END)
        return builder.compile(checkpointer=checkpointer, name="enterprise-it-support-agent")

    def _bounded_node(self, node_name: str, node: Node, *, retryable: bool = False) -> Node:
        async def execute(state: AgentState) -> dict[str, Any]:
            working_state = AgentState(**state)
            allowed_retries = self._limits.max_retries if retryable else 0
            for attempt in range(allowed_retries + 1):
                if working_state["node_count"] >= self._limits.max_nodes:
                    raise AgentNodeLimitError
                started = monotonic()
                attempt_state = AgentState(**working_state)
                attempt_state["current_node"] = node_name
                attempt_state["node_count"] = attempt_state["node_count"] + 1
                if attempt > 0:
                    attempt_state["error"] = None
                try:
                    async with asyncio.timeout(self._limits.node_timeout_seconds):
                        update = await node(attempt_state)
                except GraphInterrupt:
                    raise
                except Exception as exception:
                    exhausted = attempt >= allowed_retries
                    error_code = (
                        f"{node_name}_timeout"
                        if isinstance(exception, TimeoutError)
                        else f"{node_name}_failed"
                    )
                    attempt_state["retry_count"] = attempt_state["retry_count"] + (
                        0 if exhausted else 1
                    )
                    attempt_state["error"] = {
                        "code": error_code,
                        "message": "Agent node execution failed safely.",
                    }
                    if exhausted:
                        attempt_state["status"] = AgentRunStatus.FAILED.value
                        attempt_state["final_response"] = _safe_failure_response()
                    logger.warning(
                        "agent_node_failed",
                        extra={
                            "run_id": attempt_state["run_id"],
                            "node_name": node_name,
                            "attempt": attempt + 1,
                            "error_type": type(exception).__name__,
                            "error_code": error_code,
                        },
                    )
                    await self._run_store.save_step(
                        state=attempt_state,
                        node_name=node_name,
                        status=AgentStepStatus.FAILED,
                        latency_ms=_latency_ms(started),
                        error_code=error_code,
                        error_message="Agent node execution failed safely.",
                    )
                    if exhausted:
                        return dict(attempt_state)
                    working_state = attempt_state
                    continue

                completed_state = AgentState(**attempt_state)
                completed_state.update(update)
                if node_name != "finalize":
                    completed_state["error"] = None
                await self._run_store.save_step(
                    state=completed_state,
                    node_name=node_name,
                    status=AgentStepStatus.SUCCEEDED,
                    latency_ms=_latency_ms(started),
                )
                return dict(completed_state)
            raise AssertionError("Bounded node loop exhausted unexpectedly")

        return execute

    async def _intake(self, state: AgentState) -> dict[str, Any]:
        user_message = state["user_message"].strip()
        role = str(state["user_context"].get("role", "")).strip()
        if not user_message:
            raise ValueError("User message cannot be blank")
        if not role:
            raise ValueError("User role cannot be blank")
        update: dict[str, Any] = {
            "user_message": user_message,
            "user_context": {
                **state["user_context"],
                "role": role,
            },
            "planned_steps": ["classify_intent"],
        }
        if self._governance_service is not None and _is_finance_admin_request(user_message):
            update.update(
                {
                    "governance_action": FINANCE_ADMIN_ACTION,
                    "governance_tool": FINANCE_ADMIN_TOOL,
                    "governance_target_resource": FINANCE_ADMIN_TARGET,
                    "governance_risk_level": "r3",
                    "risk_level": RiskLevel.HIGH.value,
                    "planned_steps": [
                        "validate_local_identity_and_policy",
                        "collect_business_justification",
                        "wait_for_human_approval",
                        "simulate_execution_only_if_approved",
                    ],
                }
            )
        return update

    async def _evaluate_governance_policy(self, state: AgentState) -> dict[str, Any]:
        if self._governance_service is None:
            raise RuntimeError("Governance service is not configured")
        actor_id = str(state["user_context"].get("actor_id") or "").strip()
        role = str(state["user_context"].get("role") or "").strip()
        if not actor_id:
            decision = PolicyDecision.NEED_MORE_CONTEXT
        else:
            try:
                decision = await self._governance_service.evaluate_finance_admin_request(
                    actor_id=actor_id,
                    role=role,
                    business_justification=state["business_justification"],
                    request_id=state["request_id"],
                )
            except LocalUserNotFoundError:
                decision = PolicyDecision.DENY
        update: dict[str, Any] = {"governance_policy_decision": decision.value}
        if decision is PolicyDecision.NEED_MORE_CONTEXT:
            update.update(
                {
                    "status": AgentRunStatus.NEEDS_CLARIFICATION.value,
                    "missing_information": ["business_justification"],
                    "final_response": {
                        "summary": "需要补充业务理由后才能创建高风险审批。",
                        "answer": "请说明加入财务系统管理员组的具体业务理由。",
                        "diagnosis": [],
                        "citations": [],
                        "limitations": ["尚未创建审批请求, 也没有修改任何权限。"],
                        "next_steps": ["补充 business_justification 后重新提交请求。"],
                        "confidence": 1.0,
                    },
                }
            )
        elif decision is PolicyDecision.DENY:
            update.update(
                {
                    "status": AgentRunStatus.COMPLETED.value,
                    "final_response": {
                        "summary": "确定性 Policy Engine 拒绝了高风险请求。",
                        "answer": "当前本地用户或角色无权发起此请求。",
                        "diagnosis": [],
                        "citations": [],
                        "limitations": ["没有创建审批请求, 也没有执行权限修改。"],
                        "next_steps": ["请联系授权的 IT 治理人员核验身份和职责。"],
                        "confidence": 1.0,
                    },
                }
            )
        return update

    async def _create_approval_request(self, state: AgentState) -> dict[str, Any]:
        if self._governance_service is None:
            raise RuntimeError("Governance service is not configured")
        approval = await self._governance_service.create_finance_admin_approval(
            actor_id=str(state["user_context"]["actor_id"]),
            role=str(state["user_context"]["role"]),
            business_justification=str(state["business_justification"]),
            idempotency_key=str(state["user_context"]["idempotency_key"]),
            source_agent_run_id=UUID(state["run_id"]),
            request_id=state["request_id"],
        )
        return {
            "approval_request_id": str(approval.id),
            "status": AgentRunStatus.WAITING_APPROVAL.value,
            "final_response": {
                "summary": "高风险请求已提交人工审批。",
                "answer": "Agent 已暂停, 等待 approver 批准或拒绝。",
                "diagnosis": [],
                "citations": [],
                "limitations": ["审批前不会执行; 最终执行也仅为本地模拟。"],
                "next_steps": ["由 approver API 处理该审批请求。"],
                "confidence": 1.0,
            },
        }

    async def _await_human_approval(self, state: AgentState) -> dict[str, Any]:
        resume_value = interrupt(
            {
                "approval_request_id": state["approval_request_id"],
                "source_agent_run_id": state["run_id"],
            }
        )
        if not isinstance(resume_value, dict):
            raise ValueError("Approval resume payload must be an object")
        if resume_value.get("approval_request_id") != state["approval_request_id"]:
            raise ValueError("Approval resume payload does not match the checkpoint")
        decision = ApprovalDecisionValue(str(resume_value.get("decision")))
        return {
            "approval_decision": decision.value,
            "status": AgentRunStatus.RUNNING.value,
            "final_response": None,
        }

    async def _simulate_approved_action(self, state: AgentState) -> dict[str, Any]:
        if self._governance_service is None or state["approval_request_id"] is None:
            raise RuntimeError("Approval context is incomplete")
        approval = await self._governance_service.complete_simulated_execution(
            approval_request_id=UUID(state["approval_request_id"]),
            request_id=state["request_id"],
        )
        return {
            "simulated_execution": approval.simulated_result,
            "status": AgentRunStatus.COMPLETED.value,
            "final_response": {
                "summary": "审批已通过, 模拟执行成功。",
                "answer": "已模拟加入财务系统管理员组; 未修改任何真实权限系统。",
                "diagnosis": [],
                "citations": [],
                "limitations": ["结果仅为本地模拟, external_system_modified=false。"],
                "next_steps": ["可通过 Agent Run 和审批审计查看完整轨迹。"],
                "confidence": 1.0,
            },
        }

    async def _finish_rejected_action(self, state: AgentState) -> dict[str, Any]:
        return {
            "status": AgentRunStatus.COMPLETED.value,
            "final_response": {
                "summary": "审批已拒绝, Agent 已安全结束。",
                "answer": "未执行加入财务系统管理员组的操作。",
                "diagnosis": [],
                "citations": [],
                "limitations": ["没有修改任何真实权限系统。"],
                "next_steps": ["如业务条件变化, 请发起新的审批请求。"],
                "confidence": 1.0,
            },
        }

    async def _classify_intent(self, state: AgentState) -> dict[str, Any]:
        payload = {
            "user_message": state["user_message"],
            "user_context": state["user_context"],
        }
        response = await self._model_gateway.generate_structured_response(
            messages=(
                ModelMessage(role="system", content=INTENT_SYSTEM_PROMPT),
                ModelMessage(
                    role="user",
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ),
            response_schema=IntentClassification,
            prompt_version=INTENT_PROMPT_VERSION,
        )
        classification = response.value
        return {
            "intent": classification.intent.value,
            "intent_confidence": classification.confidence,
            "risk_level": classification.risk_level.value,
            "missing_information": list(classification.missing_information),
            "reasoning_summary": _routing_decision_summary(classification),
            "planned_steps": [self._intent_destination(classification.intent)],
            "classification_metadata": {
                "provider": response.metadata.provider,
                "model": response.metadata.resolved_model,
                "prompt_version": response.metadata.prompt_version,
                "attempts": response.metadata.attempts,
            },
        }

    async def _request_clarification(self, state: AgentState) -> dict[str, Any]:
        missing = state["missing_information"] or ["更具体的问题或故障现象"]
        answer = "请补充以下信息: " + "; ".join(missing) + "。"
        return {
            "final_response": _response(
                summary="需要补充信息",
                answer=answer,
                limitations=["当前意图置信度不足, 尚未进入知识检索或诊断流程。"],
                next_steps=["请补充必要信息后重新提交。"],
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.NEEDS_CLARIFICATION.value,
        }

    async def _retrieve_knowledge(self, state: AgentState) -> dict[str, Any]:
        results = await self._retriever.search(
            state["user_message"],
            self._top_k,
            SearchFilters(),
            UserContext(role=str(state["user_context"]["role"])),
        )
        return {
            "retrieved_evidence": [_serialize_search_result(result) for result in results],
            "planned_steps": ["compose_answer"],
        }

    async def _compose_answer(self, state: AgentState) -> dict[str, Any]:
        turn = await self._rag_answer_service.answer_from_results(
            question=state["user_message"],
            user_role=str(state["user_context"]["role"]),
            conversation_id=_optional_uuid(state["conversation_id"]),
            request_id=state["request_id"],
            retrieval_results=tuple(
                _deserialize_search_result(item) for item in state["retrieved_evidence"]
            ),
        )
        return {
            "conversation_id": str(turn.conversation_id),
            "final_response": turn.answer.model_dump(mode="json"),
            "status": AgentRunStatus.COMPLETED.value,
        }

    async def _vpn_diagnosis(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="get_device_info",
            arguments={"device_ref": "current"},
            next_step="vpn_check_network",
        )

    async def _vpn_check_network(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="run_mock_network_check",
            arguments={"target": "internet"},
            next_step="vpn_check_client",
        )

    async def _vpn_check_client(self, state: AgentState) -> dict[str, Any]:
        diagnostic_context = dict(state["diagnostic_context"])
        device = _observation(state, "get_device_info")
        if device is None:
            return {
                "escalation_reason": "无法确认设备与 VPN 客户端状态。",
                "planned_steps": ["escalate_to_human"],
            }
        diagnostic_context["vpn_client_issue"] = (
            "not_installed"
            if not device["vpn_client_installed"]
            else "not_running"
            if not device["vpn_client_running"]
            else None
        )
        return {
            "diagnostic_context": diagnostic_context,
            "planned_steps": ["vpn_check_service"],
        }

    async def _vpn_check_service(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="get_vpn_service_status",
            arguments={"region": "global"},
            next_step="vpn_check_incidents",
        )

    async def _vpn_check_incidents(self, state: AgentState) -> dict[str, Any]:
        update = await self._execute_tool(
            state,
            tool_name="search_existing_incidents",
            arguments={"service": "vpn"},
            next_step="vpn_search_knowledge",
        )
        return _mark_service_escalation(
            update,
            service_tool="get_vpn_service_status",
            incident_label="VPN",
        )

    async def _vpn_search_knowledge(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="search_knowledge",
            arguments={"area": "vpn", "query": state["user_message"]},
            next_step="vpn_complete",
            require_nonempty_results=True,
        )

    async def _vpn_complete(self, state: AgentState) -> dict[str, Any]:
        device = _observation(state, "get_device_info") or {}
        network = _observation(state, "run_mock_network_check") or {}
        service = _observation(state, "get_vpn_service_status") or {}
        incidents = _observation(state, "search_existing_incidents") or {}
        client_issue = state["diagnostic_context"].get("vpn_client_issue")
        operating_system = (
            f"{device.get('os_family', 'unknown')} {device.get('os_version', '')}".strip()
        )
        diagnosis = [
            f"操作系统: {operating_system}",
            f"公网访问: {'可达' if network.get('reachable') else '不可达'}",
            (
                "VPN 客户端: 已启动"
                if client_issue is None
                else "VPN 客户端: 未安装"
                if client_issue == "not_installed"
                else "VPN 客户端: 未启动"
            ),
            f"VPN 服务: {service.get('status', 'unknown')}",
            f"已知事件数: {len(incidents.get('incidents', []))}",
        ]
        steps = _knowledge_steps(state)
        return {
            "final_response": _response(
                summary="VPN Mock 诊断完成",
                answer="已完成设备、公网、客户端、服务和事件的只读检查。",
                diagnosis=diagnosis,
                limitations=["所有 observation 来自本地 Mock 工具, 未修改设备或企业系统。"],
                next_steps=steps,
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.COMPLETED.value,
        }

    async def _outlook_diagnosis(self, state: AgentState) -> dict[str, Any]:
        diagnostic_context = dict(state["diagnostic_context"])
        diagnostic_context["outlook_report"] = _parse_outlook_report(state["user_message"])
        return {
            "diagnostic_context": diagnostic_context,
            "planned_steps": ["outlook_check_service"],
        }

    async def _outlook_check_service(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="get_mail_service_status",
            arguments={"region": "global"},
            next_step="outlook_check_account",
        )

    async def _outlook_check_account(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="get_account_status",
            arguments={"account_ref": "current"},
            next_step="outlook_check_incidents",
        )

    async def _outlook_check_incidents(self, state: AgentState) -> dict[str, Any]:
        update = await self._execute_tool(
            state,
            tool_name="search_existing_incidents",
            arguments={"service": "mail"},
            next_step="outlook_search_knowledge",
        )
        return _mark_service_escalation(
            update,
            service_tool="get_mail_service_status",
            incident_label="邮件",
        )

    async def _outlook_search_knowledge(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="search_knowledge",
            arguments={"area": "outlook", "query": state["user_message"]},
            next_step="outlook_complete",
            require_nonempty_results=True,
        )

    async def _outlook_complete(self, state: AgentState) -> dict[str, Any]:
        report = state["diagnostic_context"].get("outlook_report", {})
        service = _observation(state, "get_mail_service_status") or {}
        account = _observation(state, "get_account_status") or {}
        missing = [
            label
            for key, label in (
                ("all_mail_affected", "是否所有邮件都收不到"),
                ("error_code_reported", "是否存在错误代码"),
                ("access_channel", "使用客户端还是 Web 端"),
            )
            if report.get(key) is None
        ]
        diagnosis = [
            f"所有邮件受影响: {_display_optional_bool(report.get('all_mail_affected'))}",
            (
                f"错误代码: {report.get('error_code')}"
                if report.get("error_code_reported")
                else f"存在错误代码: {_display_optional_bool(report.get('error_code_reported'))}"
            ),
            f"访问方式: {report.get('access_channel') or 'unknown'}",
            f"邮件服务: {service.get('status', 'unknown')}",
            (
                "账号状态: 锁定"
                if account.get("locked")
                else "账号状态: 密码已过期"
                if account.get("password_expired")
                else "账号状态: 正常"
            ),
        ]
        steps = _knowledge_steps(state)
        if missing:
            return {
                "missing_information": missing,
                "final_response": _response(
                    summary="Outlook 诊断需要补充信息",
                    answer="只读状态检查已完成, 但仍需要用户侧现象才能选择下一步。",
                    diagnosis=diagnosis,
                    limitations=["未获得完整的 Outlook 故障现象。"],
                    next_steps=["请补充: " + "; ".join(missing) + "。", *steps],
                    confidence=state["intent_confidence"],
                ),
                "status": AgentRunStatus.NEEDS_CLARIFICATION.value,
            }
        return {
            "final_response": _response(
                summary="Outlook Mock 诊断完成",
                answer="已结合用户现象、邮件服务和账号状态完成只读诊断。",
                diagnosis=diagnosis,
                limitations=["所有服务和账号 observation 均来自本地 Mock 工具。"],
                next_steps=steps,
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.COMPLETED.value,
        }

    async def _account_diagnosis(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="get_account_status",
            arguments={"account_ref": "current"},
            next_step="account_check_incidents",
        )

    async def _account_check_incidents(self, state: AgentState) -> dict[str, Any]:
        update = await self._execute_tool(
            state,
            tool_name="search_existing_incidents",
            arguments={"service": "identity"},
            next_step="account_search_knowledge",
        )
        diagnostic_context = update.get("diagnostic_context", {})
        observations = diagnostic_context.get("observations", {})
        incident_observation = observations.get("search_existing_incidents", {})
        if update.get("escalation_reason") is None and incident_observation.get("incidents"):
            update["escalation_reason"] = "发现身份系统已知事件, 建议由人工 IT 跟进。"
            update["planned_steps"] = ["escalate_to_human"]
        return update

    async def _account_search_knowledge(self, state: AgentState) -> dict[str, Any]:
        return await self._execute_tool(
            state,
            tool_name="search_knowledge",
            arguments={"area": "account", "query": state["user_message"]},
            next_step="account_complete",
            require_nonempty_results=True,
        )

    async def _account_complete(self, state: AgentState) -> dict[str, Any]:
        account = _observation(state, "get_account_status") or {}
        incidents = _observation(state, "search_existing_incidents") or {}
        diagnosis = [
            f"账号锁定: {'是' if account.get('locked') else '否'}",
            f"密码过期: {'是' if account.get('password_expired') else '否'}",
            f"MFA 状态: {account.get('mfa_state', 'unknown')}",
            f"身份系统已知事件数: {len(incidents.get('incidents', []))}",
        ]
        return {
            "final_response": _response(
                summary="账号 Mock 诊断完成",
                answer="已完成账号锁定、密码、MFA 和身份系统事件的只读检查。",
                diagnosis=diagnosis,
                limitations=["没有执行解锁、密码重置、MFA 修改或其他写操作。"],
                next_steps=_knowledge_steps(state),
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.COMPLETED.value,
        }

    async def _execute_tool(
        self,
        state: AgentState,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        next_step: str,
        require_nonempty_results: bool = False,
    ) -> dict[str, Any]:
        if state["tool_call_count"] >= self._limits.max_tool_calls:
            return {
                "escalation_reason": "已达到单次诊断的最大工具调用次数。",
                "planned_steps": ["escalate_to_human"],
            }
        try:
            result = await self._tool_gateway.execute(
                ToolExecutionRequest(
                    tool_name=tool_name,
                    arguments=arguments,
                    context=ToolExecutionContext(
                        run_id=UUID(state["run_id"]),
                        request_id=state["request_id"],
                        node_name=str(state["current_node"]),
                        user_role=str(state["user_context"]["role"]),
                    ),
                )
            )
        except ToolAuditUnavailableError:
            return {
                "escalation_reason": "工具审计不可用, 诊断已停止。",
                "planned_steps": ["escalate_to_human"],
            }
        except Exception as exception:
            logger.warning(
                "tool_gateway_failed",
                extra={
                    "run_id": state["run_id"],
                    "node_name": state["current_node"],
                    "tool_name": tool_name,
                    "error_type": type(exception).__name__,
                },
            )
            return {
                "escalation_reason": "工具网关发生受控错误, 诊断已停止。",
                "planned_steps": ["escalate_to_human"],
            }

        tool_results = [*state["tool_results"], result.as_state_value()]
        diagnostic_context = dict(state["diagnostic_context"])
        observations = dict(diagnostic_context.get("observations", {}))
        escalation_reason = state["escalation_reason"]
        if result.succeeded:
            observations[tool_name] = result.observation
            if require_nonempty_results and not (result.observation or {}).get("results"):
                escalation_reason = "没有找到可用的 Mock 知识步骤。"
        else:
            error_code = "tool_failed" if result.error is None else result.error.code
            escalation_reason = f"只读工具调用失败: {error_code}。"
        diagnostic_context["observations"] = observations
        return {
            "tool_results": tool_results,
            "tool_call_count": state["tool_call_count"] + 1,
            "diagnostic_context": diagnostic_context,
            "escalation_reason": escalation_reason,
            "planned_steps": ["escalate_to_human" if escalation_reason is not None else next_step],
        }

    async def _ticket_unavailable(self, state: AgentState) -> dict[str, Any]:
        return {
            "final_response": _response(
                summary="工单功能尚未开放",
                answer="已识别到工单请求, 但当前阶段不会创建、更新或写入任何工单。",
                limitations=["Phase 7 仍不包含工单写操作。"],
                next_steps=["请使用现有人工 IT 支持渠道提交工单。"],
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.COMPLETED.value,
        }

    async def _escalate_to_human(self, state: AgentState) -> dict[str, Any]:
        high_risk = state["risk_level"] == RiskLevel.HIGH.value
        answer = (
            "该请求可能涉及高风险或不受支持的操作, 当前 Agent 不会继续执行。"
            if high_risk
            else state["escalation_reason"]
            or (
                "诊断节点发生受控错误, 当前流程已停止。"
                if state["error"]
                else "该请求不在当前支持范围内, 建议联系人工 IT 支持。"
            )
        )
        return {
            "final_response": _response(
                summary="请求已安全升级" if not high_risk else "请求无法由当前 Agent 处理",
                answer=answer,
                diagnosis=_diagnostic_summary(state),
                limitations=[
                    "没有执行真实系统修改、命令或工单写入。",
                    "如存在工具结果, 其来源仅为本地 Mock Adapter。",
                ],
                next_steps=["请联系授权的人工 IT 支持人员。"],
                confidence=state["intent_confidence"],
            ),
            "status": AgentRunStatus.ESCALATED.value,
        }

    async def _finalize(self, state: AgentState) -> dict[str, Any]:
        if state["final_response"] is None:
            return {
                "final_response": _safe_failure_response(),
                "status": AgentRunStatus.FAILED.value,
                "error": state["error"]
                or {
                    "code": "missing_final_response",
                    "message": "Agent ended without a final response.",
                },
            }
        return {}

    def _route_after_intake(self, state: AgentState) -> str:
        if state["error"]:
            return "finalize"
        if state["governance_action"] is not None:
            return "evaluate_governance_policy"
        return "classify_intent"

    @staticmethod
    def _route_after_governance_policy(state: AgentState) -> str:
        return (
            "create_approval_request"
            if state["governance_policy_decision"] == PolicyDecision.REQUIRE_APPROVAL.value
            else "finalize"
        )

    @staticmethod
    def _route_after_human_approval(state: AgentState) -> str:
        return (
            "simulate_approved_action"
            if state["approval_decision"] == ApprovalDecisionValue.APPROVE.value
            else "finish_rejected_action"
        )

    def _route_after_classification(self, state: AgentState) -> str:
        if state["error"]:
            return "finalize"
        if state["intent_confidence"] < self._limits.confidence_threshold:
            return "request_clarification"
        if state["risk_level"] == RiskLevel.HIGH.value:
            return "escalate_to_human"
        intent = AgentIntent(state["intent"])
        return self._intent_destination(intent)

    @staticmethod
    def _route_after_retrieval(state: AgentState) -> str:
        return "finalize" if state["error"] else "compose_answer"

    @staticmethod
    def _route_vpn_after_incidents(state: AgentState) -> str:
        return "escalate_to_human" if _diagnostic_failed(state) else "vpn_search_knowledge"

    @staticmethod
    def _route_outlook_after_incidents(state: AgentState) -> str:
        return "escalate_to_human" if _diagnostic_failed(state) else "outlook_search_knowledge"

    @staticmethod
    def _route_account_after_incidents(state: AgentState) -> str:
        return "escalate_to_human" if _diagnostic_failed(state) else "account_search_knowledge"

    @staticmethod
    def _intent_destination(intent: AgentIntent) -> str:
        return {
            AgentIntent.KNOWLEDGE_QUESTION: "retrieve_knowledge",
            AgentIntent.VPN_DIAGNOSIS: "vpn_diagnosis",
            AgentIntent.OUTLOOK_DIAGNOSIS: "outlook_diagnosis",
            AgentIntent.ACCOUNT_DIAGNOSIS: "account_diagnosis",
            AgentIntent.TICKET_REQUEST: "ticket_unavailable",
            AgentIntent.UNSUPPORTED_REQUEST: "escalate_to_human",
        }[intent]

    async def _record_runtime_failure(self, run_id: UUID, error_code: str) -> None:
        stored = await self._run_store.get(run_id)
        state = AgentState(**stored.state)
        state["current_node"] = "runtime_guard"
        state["status"] = AgentRunStatus.FAILED.value
        state["error"] = {
            "code": error_code,
            "message": "Agent runtime limit was reached safely.",
        }
        state["final_response"] = _safe_failure_response()
        await self._run_store.save_step(
            state=state,
            node_name="runtime_guard",
            status=AgentStepStatus.FAILED,
            latency_ms=0,
            error_code=error_code,
            error_message="Agent runtime limit was reached safely.",
        )

    def _config(self, run_id: UUID) -> dict[str, Any]:
        return {
            "configurable": {"thread_id": str(run_id)},
            "recursion_limit": self._limits.max_nodes,
        }


def _latency_ms(started: float) -> int:
    return max(0, int((monotonic() - started) * 1000))


def _state_from_graph_values(values: dict[str, Any]) -> AgentState:
    """Drop LangGraph control metadata before JSON business-state persistence."""
    return AgentState(**{key: values[key] for key in AgentState.__annotations__ if key in values})


def _is_finance_admin_request(message: str) -> bool:
    normalized = message.casefold()
    return (
        "财务系统管理员组" in normalized
        or "finance system administrator group" in normalized
        or "finance admin group" in normalized
    )


def _routing_decision_summary(classification: IntentClassification) -> str:
    """Create the only decision explanation allowed into persisted Agent state."""
    return (
        f"路由意图为 {classification.intent.value}; "
        f"置信度 {classification.confidence:.2f}; "
        f"风险等级 {classification.risk_level.value}。"
    )


def _optional_uuid(value: str | None) -> UUID | None:
    return None if value is None else UUID(value)


def _serialize_search_result(result: SearchResult) -> dict[str, Any]:
    return {
        "chunk_id": str(result.chunk_id),
        "document_id": str(result.document_id),
        "document_title": result.document_title,
        "document_version": result.document_version,
        "content": result.content,
        "section_title": result.section_title,
        "rrf_score": result.rrf_score,
        "keyword_score": result.keyword_score,
        "vector_similarity": result.vector_similarity,
        "retrieval_method": result.retrieval_method.value,
        "citation": {
            "document_title": result.citation.document_title,
            "document_version": result.citation.document_version,
            "section_title": result.citation.section_title,
            "chunk_id": str(result.citation.chunk_id),
        },
    }


def _deserialize_search_result(value: dict[str, Any]) -> SearchResult:
    citation = value["citation"]
    return SearchResult(
        chunk_id=UUID(value["chunk_id"]),
        document_id=UUID(value["document_id"]),
        document_title=value["document_title"],
        document_version=value["document_version"],
        content=value["content"],
        section_title=value["section_title"],
        rrf_score=value["rrf_score"],
        keyword_score=value["keyword_score"],
        vector_similarity=value["vector_similarity"],
        retrieval_method=RetrievalMethod(value["retrieval_method"]),
        citation=Citation(
            document_title=citation["document_title"],
            document_version=citation["document_version"],
            section_title=citation["section_title"],
            chunk_id=UUID(citation["chunk_id"]),
        ),
    )


def _diagnostic_route(destination: str) -> Callable[[AgentState], str]:
    def route(state: AgentState) -> str:
        return "escalate_to_human" if _diagnostic_failed(state) else destination

    return route


def _diagnostic_failed(state: AgentState) -> bool:
    return state["error"] is not None or state["escalation_reason"] is not None


def _observation(state: AgentState, tool_name: str) -> dict[str, Any] | None:
    observations = state["diagnostic_context"].get("observations", {})
    value = observations.get(tool_name)
    return value if isinstance(value, dict) else None


def _mark_service_escalation(
    update: dict[str, Any],
    *,
    service_tool: str,
    incident_label: str,
) -> dict[str, Any]:
    if update.get("escalation_reason") is not None:
        return update
    diagnostic_context = update.get("diagnostic_context", {})
    observations = diagnostic_context.get("observations", {})
    service = observations.get(service_tool, {})
    incidents = observations.get("search_existing_incidents", {})
    if service.get("status") in {"degraded", "outage"}:
        update["escalation_reason"] = (
            f"{incident_label}服务状态为 {service['status']}, 建议由人工 IT 跟进。"
        )
        update["planned_steps"] = ["escalate_to_human"]
    elif incidents.get("incidents"):
        update["escalation_reason"] = f"发现{incident_label}已知事件, 建议由人工 IT 跟进。"
        update["planned_steps"] = ["escalate_to_human"]
    return update


def _knowledge_steps(state: AgentState) -> list[str]:
    knowledge = _observation(state, "search_knowledge") or {}
    steps: list[str] = []
    for item in knowledge.get("results", [])[:5]:
        steps.extend(str(step) for step in item.get("steps", [])[:8])
    return steps or ["请联系人工 IT 支持并提供本次 Agent Run ID。"]


def _parse_outlook_report(message: str) -> dict[str, Any]:
    normalized = message.casefold()
    all_mail_affected: bool | None
    if any(term in normalized for term in ("all mail", "all email", "所有邮件", "全部邮件")):
        all_mail_affected = True
    elif any(term in normalized for term in ("some mail", "some email", "部分邮件", "个别邮件")):
        all_mail_affected = False
    else:
        all_mail_affected = None

    no_error = any(
        term in normalized for term in ("no error", "without error", "没有错误", "无错误代码")
    )
    error_match = re.search(
        r"\b(?:0x[0-9a-f]+|[45]\d{2}|error[\s:#-]+[a-z0-9-]+)\b",
        normalized,
    )
    error_code = None if error_match is None else error_match.group(0)
    error_code_reported = False if no_error else True if error_code else None

    if any(term in normalized for term in ("web", "browser", "owa", "网页", "web 端")):
        access_channel = "web"
    elif any(term in normalized for term in ("desktop", "client", "app", "客户端", "桌面端")):
        access_channel = "client"
    else:
        access_channel = None
    return {
        "all_mail_affected": all_mail_affected,
        "error_code_reported": error_code_reported,
        "error_code": error_code,
        "access_channel": access_channel,
    }


def _display_optional_bool(value: bool | None) -> str:
    return "是" if value is True else "否" if value is False else "unknown"


def _diagnostic_summary(state: AgentState) -> list[str]:
    return [f"{result['tool_name']}: {result['status']}" for result in state["tool_results"][:10]]


def _response(
    *,
    summary: str,
    answer: str,
    limitations: list[str],
    next_steps: list[str],
    confidence: float,
    diagnosis: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "summary": summary,
        "answer": answer,
        "diagnosis": diagnosis or [],
        "citations": [],
        "limitations": limitations,
        "next_steps": next_steps,
        "confidence": confidence,
    }


def _safe_failure_response() -> dict[str, Any]:
    return _response(
        summary="请求未能完成",
        answer="Agent 已安全停止, 未执行任何真实系统修改或写操作。",
        limitations=["运行时发生受控错误或达到执行限制。"],
        next_steps=["请稍后重试, 或联系人工 IT 支持。"],
        confidence=0.0,
    )
