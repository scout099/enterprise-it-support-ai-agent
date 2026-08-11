"""Application composition helper tests."""

import json

from apps.dependencies import _fake_rag_response

from enterprise_it_support.agent_runtime.rag import RAGModelOutput
from enterprise_it_support.intelligence.model_gateway import FakeModelCall, ModelMessage


def _rag_call(question: str, context: list[dict[str, object]]) -> FakeModelCall:
    return FakeModelCall(
        messages=(
            ModelMessage(
                role="user",
                content=json.dumps({"question": question, "context": context}),
            ),
        ),
        response_schema=RAGModelOutput,
        prompt_version="rag-answer-v1",
    )


def test_fake_rag_refuses_when_only_document_scope_terms_overlap() -> None:
    response = _fake_rag_response(
        _rag_call(
            "What does the VPN SOP say about cafeteria meal reimbursement?",
            [
                {
                    "evidence_id": "E1",
                    "document_title": "VPN Configuration SOP",
                    "section_title": "Overview",
                    "content": "Use the demonstration VPN endpoint.",
                    "keyword_score": 0.4,
                }
            ],
        )
    )

    assert response["answerable"] is False
    assert response["evidence_ids"] == []


def test_fake_rag_prefers_subject_support_over_generic_document_overlap() -> None:
    response = _fake_rag_response(
        _rag_call(
            "What does the VPN guide say about the device clock?",
            [
                {
                    "evidence_id": "E1",
                    "document_title": "VPN Configuration SOP",
                    "section_title": "Overview",
                    "content": "This guide describes the demonstration VPN service.",
                    "keyword_score": 0.4,
                },
                {
                    "evidence_id": "E2",
                    "document_title": "VPN Configuration SOP",
                    "section_title": "Troubleshooting",
                    "content": "Confirm the device clock is correct before retrying.",
                    "keyword_score": 0.2,
                },
            ],
        )
    )

    assert response["answerable"] is True
    assert response["evidence_ids"] == ["E2"]


def test_fake_rag_matches_simple_plural_question_term_to_singular_evidence() -> None:
    response = _fake_rag_response(
        _rag_call(
            "What does the account FAQ say about passwords?",
            [
                {
                    "evidence_id": "E1",
                    "document_title": "Account FAQ",
                    "section_title": "Password recovery",
                    "content": "Use the approved password recovery channel.",
                    "keyword_score": 0.3,
                }
            ],
        )
    )

    assert response["answerable"] is True
    assert response["evidence_ids"] == ["E1"]
