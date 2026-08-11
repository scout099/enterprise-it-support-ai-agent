"""Shared application-service construction for API and CLI entry points."""

import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from enterprise_it_support.agent_runtime.state import AgentIntent, IntentClassification
from enterprise_it_support.intelligence.embeddings import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from enterprise_it_support.intelligence.model_gateway import (
    FakeModelCall,
    FakeModelGateway,
    ModelGateway,
    OpenAICompatibleModelGateway,
)
from enterprise_it_support.knowledge.indexing import (
    EmbeddingProfile,
    IndexingRepository,
    IndexingService,
)
from enterprise_it_support.knowledge.retrieval import (
    KnowledgeRetriever,
    RelevancePolicy,
    RetrievalRepository,
    extract_keyword_terms,
)
from enterprise_it_support.platform.config import (
    EmbeddingProviderType,
    ModelProviderType,
    Settings,
)
from enterprise_it_support.service_desk.persistence import (
    PendingConfirmationRepository,
    TicketRepository,
)
from enterprise_it_support.service_desk.tools import (
    ServiceDeskToolAdapter,
    create_service_desk_tool_registry,
    service_desk_permissions,
)
from enterprise_it_support.tools.gateway import (
    RolePermissionPolicy,
    ToolExecutionGateway,
    ToolExecutionStore,
)
from enterprise_it_support.tools.mock import (
    create_mock_tool_registry,
    default_tool_permissions,
)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured adapter without exposing credentials to business code."""
    if settings.embedding_provider is EmbeddingProviderType.FAKE:
        return FakeEmbeddingProvider(dimension=settings.embedding_dimension)

    assert settings.embedding_api_key is not None
    return OpenAIEmbeddingProvider(
        api_key=settings.embedding_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        base_url=settings.embedding_base_url,
    )


def build_indexing_service(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> IndexingService:
    """Build indexing with one immutable Profile from validated Settings."""
    return IndexingService(
        repository=IndexingRepository(session_factory),
        provider=build_embedding_provider(settings),
        profile=EmbeddingProfile(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            version=settings.embedding_version,
        ),
        batch_size=settings.embedding_batch_size,
    )


def build_knowledge_retriever(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> KnowledgeRetriever:
    """Build authorized hybrid retrieval with the configured Embedding Profile."""
    return KnowledgeRetriever(
        repository=RetrievalRepository(session_factory),
        provider=build_embedding_provider(settings),
        profile=EmbeddingProfile(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            version=settings.embedding_version,
        ),
        embedding_timeout_seconds=settings.retrieval_embedding_timeout_seconds,
    )


def build_model_gateway(settings: Settings) -> ModelGateway:
    """Build the bounded structured chat-model adapter from validated Settings."""
    if settings.model_provider is ModelProviderType.FAKE:
        return FakeModelGateway(
            [],
            model_name=settings.model_name,
            response_factory=_fake_model_response,
        )

    assert settings.model_api_key is not None
    return OpenAICompatibleModelGateway(
        api_key=settings.model_api_key.get_secret_value(),
        base_url=settings.model_base_url,
        model=settings.model_name,
        timeout_seconds=settings.model_timeout_seconds,
        max_attempts=settings.model_max_attempts,
        max_output_tokens=settings.model_max_output_tokens,
    )


def build_relevance_policy(settings: Settings) -> RelevancePolicy:
    """Build thresholds calibrated for the configured Embedding Profile."""
    vector_threshold = (
        None
        if settings.embedding_provider is EmbeddingProviderType.FAKE
        else settings.rag_min_vector_similarity
    )
    return RelevancePolicy(
        min_keyword_score=settings.rag_min_keyword_score,
        min_vector_similarity=vector_threshold,
    )


def build_tool_gateway(
    execution_store: ToolExecutionStore,
    *,
    ticket_repository: TicketRepository | None = None,
    confirmation_repository: PendingConfirmationRepository | None = None,
) -> ToolExecutionGateway:
    """Build the only Agent-visible path to read-only and local ticket tools."""
    registry = create_mock_tool_registry()
    permissions = default_tool_permissions()
    if ticket_repository is not None:
        create_service_desk_tool_registry(
            ServiceDeskToolAdapter(ticket_repository),
            registry=registry,
        )
        for role, grants in service_desk_permissions().items():
            permissions[role] = permissions.get(role, frozenset()) | grants
    return ToolExecutionGateway(
        registry=registry,
        policy=RolePermissionPolicy(permissions),
        execution_store=execution_store,
        confirmation_validator=confirmation_repository,
    )


def _fake_model_response(call: FakeModelCall) -> dict[str, object]:
    """Dispatch deterministic local outputs by the requested strict Schema."""
    if call.response_schema is IntentClassification:
        return _fake_intent_response(call)
    return _fake_rag_response(call)


def _fake_intent_response(call: FakeModelCall) -> dict[str, object]:
    """Classify common demo requests without pretending this is a learned model."""
    try:
        payload = json.loads(call.messages[-1].content)
        message = str(payload["user_message"]).casefold()
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exception:
        raise ValueError("Fake classifier received an invalid request payload") from exception

    ticket_terms = ("ticket", "工单", "case")
    unsafe_terms = ("disable security", "bypass", "steal", "删除审计", "绕过")
    diagnosis_terms = (
        "cannot",
        "can't",
        "wont",
        "won't",
        "error",
        "failed",
        "locked",
        "not working",
        "无法",
        "不能",
        "失败",
        "报错",
        "锁定",
    )
    area_intents = (
        (("vpn", "虚拟专用网"), AgentIntent.VPN_DIAGNOSIS),
        (("outlook", "mail", "邮箱", "邮件"), AgentIntent.OUTLOOK_DIAGNOSIS),
        (("account", "password", "账号", "密码"), AgentIntent.ACCOUNT_DIAGNOSIS),
    )

    if any(term in message for term in unsafe_terms):
        intent = AgentIntent.UNSUPPORTED_REQUEST
        confidence = 0.98
        risk_level = "high"
        missing_information: list[str] = []
    elif any(term in message for term in ticket_terms):
        intent = AgentIntent.TICKET_REQUEST
        confidence = 0.95
        risk_level = "medium"
        missing_information = []
    else:
        matched_area = next(
            (
                area_intent
                for terms, area_intent in area_intents
                if any(term in message for term in terms)
            ),
            None,
        )
        if matched_area is not None and any(term in message for term in diagnosis_terms):
            intent = matched_area
            confidence = 0.9
            risk_level = "low"
            missing_information = []
        elif matched_area is not None:
            intent = AgentIntent.KNOWLEDGE_QUESTION
            confidence = 0.85
            risk_level = "low"
            missing_information = []
        else:
            intent = AgentIntent.UNSUPPORTED_REQUEST
            confidence = 0.4
            risk_level = "low"
            missing_information = ["具体 IT 系统、问题或目标"]

    return {
        "intent": intent.value,
        "confidence": confidence,
        "risk_level": risk_level,
        "missing_information": missing_information,
        "reasoning_summary": "基于请求主题、故障措辞和当前支持范围完成简短路由。",
    }


def _fake_rag_response(call: FakeModelCall) -> dict[str, object]:
    """Produce a repeatable local answer from the strongest keyword-overlap evidence."""
    try:
        payload = json.loads(call.messages[-1].content)
        context = payload["context"]
        question_terms = set(extract_keyword_terms(str(payload["question"])))
        evidence = max(
            context,
            key=lambda item: (
                len(
                    question_terms
                    & set(
                        extract_keyword_terms(
                            " ".join(
                                (
                                    str(item["document_title"]),
                                    str(item["section_title"] or ""),
                                    str(item["content"]),
                                )
                            )
                        )
                    )
                ),
                float(item["keyword_score"]) if item["keyword_score"] is not None else -1.0,
            ),
        )
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exception:
        raise ValueError("Fake RAG model received an invalid Context payload") from exception

    content = " ".join(str(evidence["content"]).split())
    document_title = str(evidence["document_title"])
    return {
        "summary": f"来自 {document_title} 的知识库回答",
        "answer": f"企业知识库片段说明: {content[:1200]}",
        "diagnosis": [f"企业知识库: 已检索到 {document_title} 的相关片段."],
        "evidence_ids": [str(evidence["evidence_id"])],
        "limitations": ["Fake model 仅用于本地演示结构化 RAG 流程."],
        "next_steps": ["企业知识库: 请按照引用片段操作并核对结果."],
        "confidence": 0.75,
        "answerable": True,
    }
