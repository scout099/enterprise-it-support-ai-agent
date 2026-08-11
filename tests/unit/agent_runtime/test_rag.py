"""Grounded RAG service behavior tests."""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from enterprise_it_support.agent_runtime.rag import (
    RAG_PROMPT_VERSION,
    RAGAnswerService,
    RAGCitationValidationError,
)
from enterprise_it_support.conversation.repository import SavedTurn, StoredConversation
from enterprise_it_support.intelligence.model_gateway import (
    FakeModelGateway,
    ModelGatewayResponseError,
)
from enterprise_it_support.knowledge.retrieval import (
    Citation,
    RetrievalMethod,
    SearchResult,
)


class FakeRetriever:
    def __init__(self, results):
        self.results = tuple(results)
        self.calls = []

    async def search(self, query, top_k, filters, user_context):
        self.calls.append((query, top_k, filters, user_context))
        return self.results


class FakeConversationStore:
    def __init__(self):
        self.saved = []

    async def save_turn(self, **kwargs):
        self.saved.append(kwargs)
        return SavedTurn(
            conversation_id=kwargs["conversation_id"] or uuid4(),
            user_message_id=uuid4(),
            assistant_message_id=uuid4(),
        )

    async def get(self, conversation_id: UUID):
        return StoredConversation(
            id=conversation_id,
            user_role="employee",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            messages=(),
        )


def search_result(*, title: str = "VPN SOP", content: str = "Use the managed VPN profile"):
    chunk_id = uuid4()
    return SearchResult(
        chunk_id=chunk_id,
        document_id=uuid4(),
        document_title=title,
        document_version=2,
        content=content,
        section_title="Configuration",
        score=0.03,
        retrieval_method=RetrievalMethod.HYBRID,
        citation=Citation(
            document_title=title,
            document_version=2,
            section_title="Configuration",
            chunk_id=chunk_id,
        ),
    )


def grounded_output(evidence_ids=None):
    return {
        "summary": "VPN 配置说明",
        "answer": "企业知识库要求使用托管 VPN 配置。",
        "diagnosis": ["企业知识库: 已找到 VPN 配置证据."],
        "evidence_ids": evidence_ids or ["E1"],
        "limitations": [],
        "next_steps": ["企业知识库: 按照引用片段配置 VPN."],
        "confidence": 0.9,
        "answerable": True,
    }


@pytest.mark.asyncio
async def test_service_answers_with_citation_materialized_from_retrieval() -> None:
    result = search_result()
    retriever = FakeRetriever([result])
    model = FakeModelGateway([grounded_output()])
    store = FakeConversationStore()
    service = RAGAnswerService(
        retriever=retriever,
        model_gateway=model,
        conversation_store=store,
        top_k=5,
        max_context_chars=4000,
    )

    turn = await service.ask(
        question="How do I configure VPN?",
        user_role="employee",
        conversation_id=None,
        request_id="rag-success",
    )

    assert turn.answer.citations[0].chunk_id == result.chunk_id
    assert turn.answer.citations[0].document_title == "VPN SOP"
    assert store.saved[0]["retrieved_chunk_ids"] == (result.chunk_id,)
    assert store.saved[0]["prompt_version"] == RAG_PROMPT_VERSION
    assert store.saved[0]["token_usage"].total_tokens == 30
    assert "Answer only from the enterprise Context" in model.calls[0].messages[0].content
    assert "pretrained knowledge" in model.calls[0].messages[0].content
    assert "answerable=false" in model.calls[0].messages[0].content
    assert "Never invent" in model.calls[0].messages[0].content
    assert "general advice" in model.calls[0].messages[0].content
    assert str(result.chunk_id) in model.calls[0].messages[1].content


@pytest.mark.asyncio
async def test_service_refuses_without_evidence_and_does_not_call_model() -> None:
    retriever = FakeRetriever([])
    model = FakeModelGateway([])
    store = FakeConversationStore()
    service = RAGAnswerService(
        retriever=retriever,
        model_gateway=model,
        conversation_store=store,
        top_k=5,
        max_context_chars=4000,
    )

    turn = await service.ask(
        question="What is the private datacenter rule?",
        user_role="employee",
        conversation_id=None,
        request_id="rag-refusal",
    )

    assert turn.answer.confidence == 0
    assert turn.answer.citations == []
    assert "不会依据模型常识猜测" in turn.answer.answer
    assert model.calls == []
    assert store.saved[0]["model_name"] == "not-called"
    assert store.saved[0]["retrieved_chunk_ids"] == ()


@pytest.mark.asyncio
async def test_service_uses_deterministic_refusal_when_model_marks_evidence_insufficient() -> None:
    output = grounded_output()
    output.update(
        {
            "answer": "This untrusted answer must be discarded.",
            "diagnosis": [],
            "evidence_ids": [],
            "limitations": ["Model limitation"],
            "next_steps": ["一般建议: Ask IT support."],
            "confidence": 0.2,
            "answerable": False,
        }
    )
    service = RAGAnswerService(
        retriever=FakeRetriever([search_result()]),
        model_gateway=FakeModelGateway([output]),
        conversation_store=FakeConversationStore(),
        top_k=5,
        max_context_chars=4000,
    )

    turn = await service.ask(
        question="Ambiguous VPN policy",
        user_role="employee",
        conversation_id=None,
        request_id="rag-model-refusal",
    )

    assert turn.answer.confidence == 0
    assert turn.answer.citations == []
    assert "untrusted answer" not in turn.answer.answer
    assert "不会依据模型常识猜测" in turn.answer.answer


@pytest.mark.asyncio
async def test_service_rejects_citation_outside_retrieved_context() -> None:
    store = FakeConversationStore()
    service = RAGAnswerService(
        retriever=FakeRetriever([search_result()]),
        model_gateway=FakeModelGateway([grounded_output(["E99"])]),
        conversation_store=store,
        top_k=5,
        max_context_chars=4000,
    )

    with pytest.raises(RAGCitationValidationError):
        await service.ask(
            question="VPN question",
            user_role="employee",
            conversation_id=None,
            request_id="rag-invalid-citation",
        )

    assert store.saved == []


@pytest.mark.asyncio
async def test_service_propagates_malformed_model_output_without_saving() -> None:
    store = FakeConversationStore()
    service = RAGAnswerService(
        retriever=FakeRetriever([search_result()]),
        model_gateway=FakeModelGateway([{"summary": "missing fields"}]),
        conversation_store=store,
        top_k=5,
        max_context_chars=4000,
    )

    with pytest.raises(ModelGatewayResponseError):
        await service.ask(
            question="VPN question",
            user_role="employee",
            conversation_id=None,
            request_id="rag-malformed",
        )

    assert store.saved == []


@pytest.mark.asyncio
async def test_service_bounds_serialized_context_before_model_call() -> None:
    model = FakeModelGateway([grounded_output()])
    service = RAGAnswerService(
        retriever=FakeRetriever([search_result(content='"quoted" VPN evidence ' * 500)]),
        model_gateway=model,
        conversation_store=FakeConversationStore(),
        top_k=5,
        max_context_chars=1000,
    )

    await service.ask(
        question="VPN question",
        user_role="employee",
        conversation_id=None,
        request_id="rag-bounded-context",
    )

    payload = json.loads(model.calls[0].messages[1].content)
    serialized_context = json.dumps(
        payload["context"],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert len(serialized_context) <= 1000
    assert len(payload["context"][0]["content"]) >= 100
