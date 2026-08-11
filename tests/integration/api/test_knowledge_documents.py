"""Knowledge document API tests against PostgreSQL."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from apps.api.main import create_app
from apps.dependencies import build_relevance_policy
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from enterprise_it_support.agent_runtime.rag import RAGAnswerService
from enterprise_it_support.intelligence.model_gateway import (
    FakeModelGateway,
    ModelGatewayResponseError,
    ModelGatewayTimeoutError,
    ModelGatewayUnavailableError,
)
from enterprise_it_support.knowledge.retrieval import RetrievalUnavailableError
from enterprise_it_support.platform.config import Environment, Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

FIXTURES = Path(__file__).parents[3] / "data" / "evaluation" / "knowledge"


class UnavailableRetriever:
    async def search(self, query, top_k, filters, user_context):
        raise RetrievalUnavailableError("fictional-provider-secret")


class MalformedRAGService:
    async def ask(self, **_kwargs):
        raise ModelGatewayResponseError("fictional-malformed-model-secret")


def upload_and_index(
    client: TestClient,
    *,
    filename: str,
    media_type: str,
    title: str,
) -> dict[str, object]:
    path = FIXTURES / filename
    upload = client.post(
        "/knowledge/documents",
        data={
            "title": title,
            "owner": "Demo IT Team",
            "source_name": "Chat API Library",
        },
        files={"file": (path.name, path.read_bytes(), media_type)},
    )
    assert upload.status_code == 201
    imported = upload.json()
    indexed = client.post(f"/knowledge/documents/{imported['document_id']}/index")
    assert indexed.status_code == 200
    assert indexed.json()["failed_chunks"] == 0
    return imported


@pytest.fixture
async def knowledge_api_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[TestClient]:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST).model_copy(
        update={
            "knowledge_storage_path": tmp_path,
            "knowledge_max_file_size_bytes": 10_000,
            "knowledge_chunk_size": 40,
            "knowledge_chunk_overlap": 5,
        }
    )
    database = DatabaseManager(settings.active_database_url)
    async with database.session_factory.begin() as session:
        await session.execute(
            text(
                "TRUNCATE agent_steps, agent_runs, messages, conversations, document_chunks, "
                "document_versions, documents, knowledge_sources CASCADE"
            )
        )
    await database.close()

    with TestClient(create_app(settings=settings)) as client:
        yield client

    get_settings.cache_clear()


@pytest.mark.integration
def test_upload_and_read_document_with_traceable_chunks(
    knowledge_api_client: TestClient,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"

    upload = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "title": "VPN Configuration SOP",
            "owner": "Demo IT Operations",
            "source_name": "Local SOP Library",
        },
        files={"file": (path.name, path.read_bytes(), "text/markdown")},
        headers={"X-Request-ID": "knowledge-upload"},
    )

    assert upload.status_code == 201
    imported = upload.json()
    assert imported["created_version"] is True
    assert imported["version"] == 1
    assert imported["chunk_count"] > 0

    documents = knowledge_api_client.get("/knowledge/documents")
    detail = knowledge_api_client.get(f"/knowledge/documents/{imported['document_id']}")
    chunks = knowledge_api_client.get(f"/knowledge/documents/{imported['document_id']}/chunks")

    assert documents.status_code == 200
    assert len(documents.json()) == 1
    assert documents.json()[0]["latest_version"] == 1
    assert detail.status_code == 200
    assert [version["version"] for version in detail.json()["versions"]] == [1]
    assert chunks.status_code == 200
    assert chunks.json()["document_version_id"] == imported["document_version_id"]
    assert all(
        chunk["document_version_id"] == imported["document_version_id"]
        for chunk in chunks.json()["chunks"]
    )
    assert all("source_location" in chunk["metadata"] for chunk in chunks.json()["chunks"])


@pytest.mark.integration
def test_duplicate_upload_returns_existing_version(
    knowledge_api_client: TestClient,
) -> None:
    path = FIXTURES / "outlook_mail_troubleshooting.txt"
    request = {
        "data": {
            "title": "Outlook Mail Troubleshooting SOP",
            "owner": "Demo Messaging Team",
            "source_name": "Local SOP Library",
        },
        "files": {"file": (path.name, path.read_bytes(), "text/plain")},
    }

    first = knowledge_api_client.post("/knowledge/documents", **request)
    duplicate = knowledge_api_client.post("/knowledge/documents", **request)

    assert first.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["created_version"] is False
    assert duplicate.json()["document_version_id"] == first.json()["document_version_id"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        ("vpn_configuration_sop.md", "text/markdown"),
        ("outlook_mail_troubleshooting.txt", "text/plain"),
        ("account_common_questions_faq.pdf", "application/pdf"),
    ],
)
def test_api_accepts_each_supported_document_format(
    knowledge_api_client: TestClient,
    filename: str,
    media_type: str,
) -> None:
    path = FIXTURES / filename

    response = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "owner": "Demo Knowledge Team",
            "source_name": "Format Acceptance Library",
        },
        files={"file": (path.name, path.read_bytes(), media_type)},
    )

    assert response.status_code == 201
    assert response.json()["chunk_count"] > 0


@pytest.mark.integration
def test_api_rejects_unsupported_document_type(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "owner": "Demo Knowledge Team",
            "source_name": "Local SOP Library",
        },
        files={"file": ("unsupported.docx", b"not a document", "application/octet-stream")},
        headers={"X-Request-ID": "unsupported-upload"},
    )

    assert response.status_code == 415
    assert response.json() == {
        "error": {
            "code": "unsupported_document_media_type",
            "message": (
                "Document filename and media type must match an allowed TXT, Markdown, or PDF "
                "format"
            ),
            "request_id": "unsupported-upload",
        }
    }


@pytest.mark.integration
def test_api_rejects_mismatched_declared_media_type(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "owner": "Demo Knowledge Team",
            "source_name": "Local SOP Library",
        },
        files={"file": ("commands.txt", b"echo not-executed", "application/x-sh")},
        headers={"X-Request-ID": "mismatched-upload"},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_document_media_type"
    assert response.json()["error"]["request_id"] == "mismatched-upload"


@pytest.mark.integration
def test_api_rejects_parser_inferred_title_longer_than_database_limit(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "owner": "Demo Knowledge Team",
            "source_name": "Local SOP Library",
        },
        files={"file": ("long-title.txt", b"A" * 501 + b"\n\nUseful body", "text/plain")},
        headers={"X-Request-ID": "long-inferred-title"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "document_ingestion_failed",
            "message": "Title cannot exceed 500 characters",
            "request_id": "long-inferred-title",
        }
    }


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "content", "media_type", "expected_status", "expected_code"),
    [
        ("empty.txt", b"", "text/plain", 422, "document_ingestion_failed"),
        ("oversized.txt", b"A" * 10_001, "text/plain", 413, "document_too_large"),
        ("broken.pdf", b"not-a-pdf", "application/pdf", 422, "document_ingestion_failed"),
    ],
)
def test_api_rejects_invalid_document_content(
    knowledge_api_client: TestClient,
    filename: str,
    content: bytes,
    media_type: str,
    expected_status: int,
    expected_code: str,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "owner": "Demo Knowledge Team",
            "source_name": "Local SOP Library",
        },
        files={"file": (filename, content, media_type)},
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["request_id"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "path_suffix",
    ["", "/chunks"],
)
def test_api_returns_not_found_for_unknown_document(
    knowledge_api_client: TestClient,
    path_suffix: str,
) -> None:
    response = knowledge_api_client.get(
        f"/knowledge/documents/00000000-0000-0000-0000-000000000000{path_suffix}",
        headers={"X-Request-ID": "unknown-document"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "knowledge_document_not_found",
            "message": "Knowledge document was not found",
            "request_id": "unknown-document",
        }
    }


@pytest.mark.integration
def test_index_document_and_read_index_status(
    knowledge_api_client: TestClient,
) -> None:
    path = FIXTURES / "vpn_configuration_sop.md"
    upload = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "title": "VPN API Indexing SOP",
            "owner": "Demo IT Operations",
            "source_name": "Index API Library",
        },
        files={"file": (path.name, path.read_bytes(), "text/markdown")},
    )
    imported = upload.json()

    indexed = knowledge_api_client.post(
        f"/knowledge/documents/{imported['document_id']}/index",
        headers={"X-Request-ID": "index-api"},
    )
    status = knowledge_api_client.get(
        f"/knowledge/documents/{imported['document_id']}/index-status"
    )
    repeated = knowledge_api_client.post(f"/knowledge/documents/{imported['document_id']}/index")
    forced = knowledge_api_client.post(
        f"/knowledge/documents/{imported['document_id']}/index",
        json={"force": True},
    )

    assert indexed.status_code == 200
    assert indexed.json()["indexed_chunks"] == imported["chunk_count"]
    assert indexed.json()["failed_chunks"] == 0
    assert indexed.json()["model"] == "fake-embedding-v1"
    assert status.status_code == 200
    assert status.json()["status"] == "indexed"
    assert status.json()["indexed_chunks"] == imported["chunk_count"]
    assert repeated.json()["indexed_chunks"] == 0
    assert repeated.json()["skipped_chunks"] == imported["chunk_count"]
    assert forced.json()["indexed_chunks"] == imported["chunk_count"]
    assert indexed.headers["X-Request-ID"] == "index-api"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path_suffix"),
    [("post", "/index"), ("get", "/index-status")],
)
def test_index_routes_return_not_found_for_unknown_document(
    knowledge_api_client: TestClient,
    method: str,
    path_suffix: str,
) -> None:
    response = getattr(knowledge_api_client, method)(
        f"/knowledge/documents/00000000-0000-0000-0000-000000000000{path_suffix}",
        headers={"X-Request-ID": "unknown-index-document"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "knowledge_document_not_found",
            "message": "Knowledge document was not found",
            "request_id": "unknown-index-document",
        }
    }


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "media_type", "title", "query"),
    [
        ("vpn_configuration_sop.md", "text/markdown", "VPN Search SOP", "VPN server"),
        (
            "outlook_mail_troubleshooting.txt",
            "text/plain",
            "Outlook Search SOP",
            "Outlook mailbox quota",
        ),
        (
            "account_common_questions_faq.pdf",
            "application/pdf",
            "Account Search FAQ",
            "Account password",
        ),
    ],
)
def test_search_api_returns_vpn_outlook_and_account_evidence_with_citations(
    knowledge_api_client: TestClient,
    filename: str,
    media_type: str,
    title: str,
    query: str,
) -> None:
    path = FIXTURES / filename
    upload = knowledge_api_client.post(
        "/knowledge/documents",
        data={
            "title": title,
            "owner": "Demo IT Team",
            "source_name": "Search API Library",
        },
        files={"file": (path.name, path.read_bytes(), media_type)},
    )
    imported = upload.json()
    indexed = knowledge_api_client.post(f"/knowledge/documents/{imported['document_id']}/index")

    response = knowledge_api_client.post(
        "/knowledge/search",
        json={
            "query": query,
            "top_k": 1,
            "filters": {"document_id": imported["document_id"]},
            "user_role": "employee",
        },
    )

    assert indexed.status_code == 200
    assert response.status_code == 200
    assert len(response.json()) == 1
    result = response.json()[0]
    assert result["document_id"] == imported["document_id"]
    assert result["document_title"] == title
    assert result["retrieval_method"] in {"keyword", "vector", "hybrid"}
    assert result["citation"] == {
        "document_title": title,
        "document_version": 1,
        "section_title": result["section_title"],
        "chunk_id": result["chunk_id"],
    }


@pytest.mark.integration
def test_search_api_returns_empty_list_when_filters_exclude_all_documents(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/search",
        json={
            "query": "VPN",
            "top_k": 5,
            "filters": {"document_id": "00000000-0000-0000-0000-000000000000"},
            "user_role": "employee",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {"query": " ", "top_k": 5, "user_role": "employee"},
        {"query": "VPN", "top_k": 0, "user_role": "employee"},
        {"query": "VPN", "top_k": 5, "user_role": " "},
    ],
)
def test_search_api_rejects_invalid_bounded_input(
    knowledge_api_client: TestClient,
    payload: dict[str, object],
) -> None:
    response = knowledge_api_client.post("/knowledge/search", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_search_api_rejects_naive_temporal_filter(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/knowledge/search",
        json={
            "query": "VPN",
            "filters": {"effective_at": "2026-07-22T10:00:00"},
            "user_role": "employee",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_search_api_maps_retrieval_dependency_failure_to_safe_503() -> None:
    settings = Settings(environment=Environment.TEST)
    with TestClient(
        create_app(settings=settings, knowledge_retriever=UnavailableRetriever())
    ) as client:
        response = client.post(
            "/knowledge/search",
            json={"query": "VPN", "top_k": 5, "user_role": "employee"},
            headers={"X-Request-ID": "retrieval-unavailable"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "Knowledge retrieval is temporarily unavailable",
            "request_id": "retrieval-unavailable",
        }
    }
    assert "fictional-provider-secret" not in response.text


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "media_type", "title", "question"),
    [
        (
            "vpn_configuration_sop.md",
            "text/markdown",
            "VPN Chat SOP",
            "How do I configure the company VPN?",
        ),
        (
            "outlook_mail_troubleshooting.txt",
            "text/plain",
            "Outlook Chat SOP",
            "What should I check when Outlook cannot send mail?",
        ),
        (
            "account_common_questions_faq.pdf",
            "application/pdf",
            "Account Chat FAQ",
            "What does the account FAQ say about passwords?",
        ),
    ],
)
def test_chat_api_answers_vpn_outlook_and_account_with_persisted_real_citations(
    knowledge_api_client: TestClient,
    filename: str,
    media_type: str,
    title: str,
    question: str,
) -> None:
    upload_and_index(
        knowledge_api_client,
        filename=filename,
        media_type=media_type,
        title=title,
    )

    response = knowledge_api_client.post(
        "/chat/ask",
        json={"question": question, "user_role": "employee"},
        headers={"X-Request-ID": "chat-grounded"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["summary"]
    assert answer["answer"]
    assert answer["diagnosis"]
    assert answer["citations"]
    assert answer["citations"][0]["document_title"] == title
    assert answer["limitations"]
    assert answer["next_steps"]
    assert 0 < answer["confidence"] <= 1
    assert answer["model_name"] == "fake-chat-v1"
    assert answer["prompt_version"] == "rag-answer-v1"
    assert answer["token_usage"]["total_tokens"] == 30
    assert answer["request_id"] == "chat-grounded"

    conversation = knowledge_api_client.get(
        f"/chat/conversations/{answer['conversation_id']}",
        params={"user_role": "employee"},
    )
    assert conversation.status_code == 200
    messages = conversation.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == question
    assert messages[1]["retrieval_query"] == question
    assert answer["citations"][0]["chunk_id"] in messages[1]["retrieved_chunk_ids"]
    assert messages[1]["model_name"] == "fake-chat-v1"
    assert messages[1]["prompt_version"] == "rag-answer-v1"
    assert messages[1]["token_usage"]["total_tokens"] == 30
    assert messages[1]["request_id"] == "chat-grounded"


@pytest.mark.integration
def test_agent_api_routes_knowledge_question_through_rag_and_persists_steps(
    knowledge_api_client: TestClient,
) -> None:
    upload_and_index(
        knowledge_api_client,
        filename="vpn_configuration_sop.md",
        media_type="text/markdown",
        title="VPN Agent SOP",
    )

    response = knowledge_api_client.post(
        "/agent/runs",
        json={
            "user_message": "How do I configure the company VPN?",
            "user_role": "employee",
        },
        headers={"X-Request-ID": "agent-grounded"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["request_id"] == "agent-grounded"
    assert run["status"] == "completed"
    assert run["intent"] == "knowledge_question"
    assert run["final_response"]["citations"][0]["document_title"] == "VPN Agent SOP"
    assert [step["node_name"] for step in run["steps"]] == [
        "intake",
        "classify_intent",
        "retrieve_knowledge",
        "compose_answer",
        "finalize",
    ]
    assert all(step["status"] == "succeeded" for step in run["steps"])
    assert run["retrieved_evidence"]
    assert run["tool_results"] == []
    assert run["tool_executions"] == []
    assert run["tool_call_count"] == 0
    assert run["classification_metadata"]["prompt_version"] == "intent-classification-v1"

    readback = knowledge_api_client.get(
        f"/agent/runs/{run['run_id']}",
        params={"user_role": "employee"},
    )
    forbidden = knowledge_api_client.get(
        f"/agent/runs/{run['run_id']}",
        params={"user_role": "administrator"},
    )

    assert readback.status_code == 200
    assert readback.json()["steps"] == run["steps"]
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "agent_run_role_mismatch"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("message", "intent", "route_node", "status", "tool_count"),
    [
        ("VPN cannot connect", "vpn_diagnosis", "vpn_diagnosis", "completed", 5),
        (
            "Outlook desktop client cannot receive all email and shows error 0x800401",
            "outlook_diagnosis",
            "outlook_diagnosis",
            "completed",
            4,
        ),
        (
            "My account is locked",
            "account_diagnosis",
            "account_diagnosis",
            "completed",
            3,
        ),
        (
            "Create an IT ticket",
            "ticket_request",
            "ticket_unavailable",
            "completed",
            0,
        ),
        (
            "Disable security controls",
            "unsupported_request",
            "escalate_to_human",
            "escalated",
            0,
        ),
    ],
)
def test_agent_api_reaches_diagnosis_and_safe_non_tool_routes(
    knowledge_api_client: TestClient,
    message: str,
    intent: str,
    route_node: str,
    status: str,
    tool_count: int,
) -> None:
    response = knowledge_api_client.post(
        "/agent/runs",
        json={"user_message": message, "user_role": "employee"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["intent"] == intent
    assert run["status"] == status
    assert route_node in [step["node_name"] for step in run["steps"]]
    assert run["retrieved_evidence"] == []
    assert run["tool_call_count"] == tool_count
    assert len(run["tool_results"]) == tool_count
    assert len(run["tool_executions"]) == tool_count
    assert all(execution["has_side_effect"] is False for execution in run["tool_executions"])
    readback = knowledge_api_client.get(
        f"/agent/runs/{run['run_id']}",
        params={"user_role": "employee"},
    )
    assert readback.status_code == 200
    assert readback.json()["tool_results"] == run["tool_results"]
    assert readback.json()["tool_executions"] == run["tool_executions"]
    if intent.endswith("_diagnosis"):
        assert "Mock 诊断" in run["final_response"]["summary"]
        assert run["final_response"]["diagnosis"]
    else:
        assert tool_count == 0


@pytest.mark.integration
def test_agent_api_low_confidence_requests_clarification(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/agent/runs",
        json={"user_message": "Please help", "user_role": "employee"},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "needs_clarification"
    assert run["intent_confidence"] < 0.65
    assert run["missing_information"]
    assert "request_clarification" in [step["node_name"] for step in run["steps"]]
    assert run["tool_call_count"] == 0
    assert run["tool_executions"] == []


@pytest.mark.integration
def test_fake_chat_prefers_stronger_keyword_evidence_over_vpn_distractor(
    knowledge_api_client: TestClient,
) -> None:
    upload_and_index(
        knowledge_api_client,
        filename="vpn_configuration_sop.md",
        media_type="text/markdown",
        title="VPN Configuration SOP",
    )
    upload_and_index(
        knowledge_api_client,
        filename="vpn_security_notice.txt",
        media_type="text/plain",
        title="VPN Security Notice",
    )

    response = knowledge_api_client.post(
        "/chat/ask",
        json={
            "question": "How do I configure the company VPN?",
            "user_role": "employee",
        },
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["citations"][0]["document_title"] == "VPN Configuration SOP"
    assert "vpn.demo.invalid" in answer["answer"]


@pytest.mark.integration
def test_chat_api_refuses_without_evidence_and_persists_zero_token_trace(
    knowledge_api_client: TestClient,
) -> None:
    response = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "What is the quantum printer policy?", "user_role": "employee"},
        headers={"X-Request-ID": "chat-no-evidence"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["confidence"] == 0
    assert answer["citations"] == []
    assert "不会依据模型常识猜测" in answer["answer"]
    assert answer["model_name"] == "not-called"
    assert answer["token_usage"]["total_tokens"] == 0

    conversation = knowledge_api_client.get(
        f"/chat/conversations/{answer['conversation_id']}",
        params={"user_role": "employee"},
    ).json()
    assert conversation["messages"][1]["retrieved_chunk_ids"] == []
    assert conversation["messages"][1]["model_name"] == "not-called"


@pytest.mark.integration
def test_chat_api_refuses_irrelevant_vector_neighbor_in_nonempty_knowledge_base(
    knowledge_api_client: TestClient,
) -> None:
    upload_and_index(
        knowledge_api_client,
        filename="vpn_configuration_sop.md",
        media_type="text/markdown",
        title="Only VPN SOP",
    )

    response = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "What is the quantum printer policy?", "user_role": "employee"},
        headers={"X-Request-ID": "chat-irrelevant-neighbor"},
    )

    assert response.status_code == 200
    answer = response.json()
    assert answer["citations"] == []
    assert answer["confidence"] == 0
    assert answer["model_name"] == "not-called"
    assert answer["token_usage"]["total_tokens"] == 0

    conversation = knowledge_api_client.get(
        f"/chat/conversations/{answer['conversation_id']}",
        params={"user_role": "employee"},
    ).json()
    assert conversation["messages"][1]["retrieved_chunk_ids"]


@pytest.mark.integration
def test_chat_api_saves_multiple_turns_and_rejects_role_change(
    knowledge_api_client: TestClient,
) -> None:
    upload_and_index(
        knowledge_api_client,
        filename="vpn_configuration_sop.md",
        media_type="text/markdown",
        title="VPN Multi-turn SOP",
    )
    first = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "How do I configure VPN?", "user_role": "employee"},
        headers={"X-Request-ID": "chat-turn-one"},
    ).json()
    second_response = knowledge_api_client.post(
        "/chat/ask",
        json={
            "question": "Which VPN server should I use?",
            "user_role": "employee",
            "conversation_id": first["conversation_id"],
        },
        headers={"X-Request-ID": "chat-turn-two"},
    )
    role_change = knowledge_api_client.post(
        "/chat/ask",
        json={
            "question": "Continue with helpdesk access",
            "user_role": "helpdesk",
            "conversation_id": first["conversation_id"],
        },
    )

    assert second_response.status_code == 200
    conversation = knowledge_api_client.get(
        f"/chat/conversations/{first['conversation_id']}",
        params={"user_role": "employee"},
    )
    assert [message["sequence_number"] for message in conversation.json()["messages"]] == [
        1,
        2,
        3,
        4,
    ]
    assert conversation.json()["messages"][3]["request_id"] == "chat-turn-two"
    assert role_change.status_code == 403
    assert role_change.json()["error"]["code"] == "conversation_role_mismatch"


@pytest.mark.integration
def test_chat_retrieval_enforces_different_role_knowledge_permissions(
    knowledge_api_client: TestClient,
) -> None:
    imported = upload_and_index(
        knowledge_api_client,
        filename="account_common_questions_faq.pdf",
        media_type="application/pdf",
        title="Restricted Account FAQ",
    )
    settings = Settings(environment=Environment.TEST)
    engine = create_engine(settings.active_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE documents SET visibility = 'role_restricted', "
                    "allowed_roles = ARRAY['helpdesk'] WHERE id = :document_id"
                ),
                {"document_id": imported["document_id"]},
            )
    finally:
        engine.dispose()

    employee = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "What is the account password policy?", "user_role": "employee"},
    )
    helpdesk = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "What is the account password policy?", "user_role": "helpdesk"},
    )

    assert employee.status_code == 200
    assert employee.json()["citations"] == []
    assert employee.json()["confidence"] == 0
    assert helpdesk.status_code == 200
    assert helpdesk.json()["citations"][0]["document_title"] == "Restricted Account FAQ"


def test_chat_api_maps_malformed_model_output_to_safe_502(test_settings: Settings) -> None:
    with TestClient(
        create_app(settings=test_settings, rag_answer_service=MalformedRAGService())
    ) as client:
        response = client.post(
            "/chat/ask",
            json={"question": "VPN question", "user_role": "employee"},
            headers={"X-Request-ID": "chat-malformed-model"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "bad_gateway",
            "message": "Model returned an invalid grounded response",
            "request_id": "chat-malformed-model",
        }
    }
    assert "fictional-malformed-model-secret" not in response.text


@pytest.mark.integration
@pytest.mark.parametrize(
    ("failure_kind", "outcome", "expected_status", "error_stage", "error_code"),
    [
        ("retrieval", None, 503, "retrieval", "retrieval_unavailable"),
        (
            "model",
            ModelGatewayTimeoutError("fictional-timeout-secret"),
            503,
            "model",
            "model_timeout",
        ),
        (
            "model",
            ModelGatewayUnavailableError("fictional-provider-secret"),
            503,
            "model",
            "model_unavailable",
        ),
        (
            "model",
            {"summary": "missing fields"},
            502,
            "validation",
            "model_response_invalid",
        ),
        (
            "model",
            {
                "summary": "VPN answer",
                "answer": "Use the managed VPN profile.",
                "diagnosis": ["企业知识库: VPN evidence found."],
                "evidence_ids": ["E99"],
                "limitations": [],
                "next_steps": ["企业知识库: Follow the VPN SOP."],
                "confidence": 0.8,
                "answerable": True,
            },
            502,
            "citation",
            "citation_invalid",
        ),
    ],
)
def test_chat_api_persists_safe_failed_trace_for_every_failure_stage(
    knowledge_api_client: TestClient,
    failure_kind: str,
    outcome,
    expected_status: int,
    error_stage: str,
    error_code: str,
) -> None:
    if failure_kind == "model":
        upload_and_index(
            knowledge_api_client,
            filename="vpn_configuration_sop.md",
            media_type="text/markdown",
            title="VPN Failure Trace SOP",
        )
    settings = knowledge_api_client.app.state.settings
    retriever = (
        UnavailableRetriever()
        if failure_kind == "retrieval"
        else knowledge_api_client.app.state.knowledge_retriever
    )
    knowledge_api_client.app.state.rag_answer_service = RAGAnswerService(
        retriever=retriever,
        model_gateway=FakeModelGateway([] if outcome is None else [outcome]),
        conversation_store=knowledge_api_client.app.state.conversation_repository,
        relevance_policy=build_relevance_policy(settings),
        top_k=settings.rag_top_k,
        max_context_chars=settings.rag_max_context_chars,
    )
    request_id = f"failed-{error_code}"

    response = knowledge_api_client.post(
        "/chat/ask",
        json={"question": "How do I configure VPN?", "user_role": "employee"},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == expected_status
    assert "fictional" not in response.text

    engine = create_engine(settings.active_database_url)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT status, error_stage, error_code, response, model_attempts, "
                    "total_tokens, request_id, content FROM messages "
                    "WHERE request_id = :request_id AND role = 'assistant'"
                ),
                {"request_id": request_id},
            ).one()
    finally:
        engine.dispose()

    assert row.status == "failed"
    assert row.error_stage == error_stage
    assert row.error_code == error_code
    assert row.response is None
    assert row.request_id == request_id
    assert "fictional" not in row.content
    if failure_kind == "retrieval":
        assert row.model_attempts == 0
        assert row.total_tokens == 0
    else:
        assert row.model_attempts == 1
