"""Deterministic metric tests independent from models, HTTP, and PostgreSQL."""

from enterprise_it_support.evaluation.dataset import EvaluationCase
from enterprise_it_support.evaluation.metrics import aggregate_metrics, evaluate_case
from enterprise_it_support.evaluation.models import (
    AgentObservation,
    TokenUsageObservation,
    ToolCallObservation,
)


def _case() -> EvaluationCase:
    return EvaluationCase.model_validate(
        {
            "case_id": "metric-01",
            "category": "knowledge_question",
            "user_query": "What is the VPN endpoint?",
            "user_context": {"actor_id": "employee-demo", "user_role": "employee"},
            "expected_intent": "knowledge_question",
            "expected_documents": [{"source_name": "Evaluation", "title": "VPN SOP"}],
            "expected_tool_calls": [
                {"tool_name": "search_knowledge", "arguments": {"area": "vpn"}}
            ],
            "expected_final_status": "completed",
            "prohibited_actions": ["external_system_modified"],
            "reference_answer": "Use vpn.demo.invalid.",
        }
    )


def _observation(**updates: object) -> AgentObservation:
    values: dict[str, object] = {
        "case_id": "metric-01",
        "category": "knowledge_question",
        "actual_intent": "knowledge_question",
        "retrieved_document_titles": ["Distractor", "VPN SOP"],
        "retrieved_chunk_ids": ["chunk-x", "chunk-vpn"],
        "evidence_texts": ["Unrelated.", "Use vpn.demo.invalid for the approved connection."],
        "citation_document_titles": ["VPN SOP"],
        "citation_chunk_ids": ["chunk-vpn"],
        "tool_calls": [
            ToolCallObservation(
                tool_name="search_knowledge",
                arguments={"area": "vpn"},
                status="succeeded",
                latency_ms=3,
            )
        ],
        "final_status": "completed",
        "final_response": {"answer": "Use vpn.demo.invalid."},
        "refused": False,
        "claims": ["企业知识库片段说明: Use vpn.demo.invalid"],
        "actual_actions": ["tool:search_knowledge"],
        "steps": ["intake", "classify_intent", "finalize"],
        "latency_ms": 20,
        "token_usage": TokenUsageObservation(
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            model_calls=1,
        ),
        "prompt_versions": ["intent-v1"],
        "model_names": ["fake-v1"],
    }
    values.update(updates)
    return AgentObservation.model_validate(values)


def test_case_metrics_calculate_rank_citation_support_and_agent_accuracy() -> None:
    result = evaluate_case(_case(), _observation())
    scores = result.deterministic_scores

    assert scores.retrieval_rank == 2
    assert scores.recall_at_3 == 1
    assert scores.recall_at_5 == 1
    assert scores.reciprocal_rank == 0.5
    assert scores.citation_validity == 1
    assert scores.evidence_coverage == 1
    assert scores.unsupported_claim_rate == 0
    assert scores.refusal_correctness is True
    assert scores.intent_accuracy is True
    assert scores.tool_selection_accuracy is True
    assert scores.tool_argument_accuracy is True
    assert scores.workflow_completion is True
    assert scores.prohibited_action is False
    assert result.failures == []


def test_case_metrics_surface_invalid_arguments_unsupported_claim_and_safety() -> None:
    observation = _observation(
        citation_chunk_ids=["invented"],
        citation_document_titles=["Invented"],
        claims=["Reset the production firewall."],
        actual_actions=["external_system_modified"],
        tool_calls=[
            ToolCallObservation(
                tool_name="search_knowledge",
                arguments={"area": "outlook"},
                status="failed",
                error_code="tool_failed",
                latency_ms=4,
            )
        ],
    )

    result = evaluate_case(_case(), observation)

    assert result.deterministic_scores.citation_validity == 0
    assert result.deterministic_scores.evidence_coverage == 0
    assert result.deterministic_scores.unsupported_claim_rate == 1
    assert result.deterministic_scores.tool_argument_accuracy is False
    assert result.deterministic_scores.prohibited_action is True
    assert set(result.failures) >= {
        "citation_invalid",
        "expected_evidence_not_cited",
        "unsupported_claim_detected",
        "tool_argument_mismatch",
        "prohibited_action_observed",
    }


def test_aggregate_metrics_keep_denominators_and_system_usage_explicit() -> None:
    successful = evaluate_case(_case(), _observation())
    failed = evaluate_case(
        _case().model_copy(update={"case_id": "metric-02"}),
        _observation(
            case_id="metric-02",
            actual_intent="unsupported_request",
            final_status="failed",
            refused=True,
        ),
    )

    report = aggregate_metrics([successful, failed])

    assert report.retrieval["recall_at_3"].value == 1
    assert report.retrieval["mrr"].value == 0.5
    assert report.agent["intent_accuracy"].value == 0.5
    assert report.agent["workflow_completion_rate"].value == 0.5
    assert report.system.latency_ms.value == 20
    assert report.system.average_steps.value == 3
    assert report.system.token_usage.total_tokens == 60
    assert report.system.token_usage.model_calls == 2
    assert report.system.average_total_tokens.value == 30


def test_recall_at_k_counts_every_expected_document() -> None:
    raw_case = _case().model_dump()
    raw_case["expected_documents"].append({"source_name": "Evaluation", "title": "VPN Security"})
    case = EvaluationCase.model_validate(raw_case)

    scores = evaluate_case(case, _observation()).deterministic_scores

    assert scores.recall_at_3 == 0.5
    assert scores.recall_at_5 == 0.5


def test_tool_argument_accuracy_excludes_cases_without_tool_calls() -> None:
    no_tool_case = _case().model_copy(update={"expected_tool_calls": []})
    no_tool_result = evaluate_case(no_tool_case, _observation(tool_calls=[]))
    with_tool_result = evaluate_case(_case(), _observation())

    report = aggregate_metrics([no_tool_result, with_tool_result])

    assert no_tool_result.deterministic_scores.tool_argument_accuracy is None
    assert report.agent["tool_argument_accuracy"].value == 1
    assert report.agent["tool_argument_accuracy"].sample_count == 1
