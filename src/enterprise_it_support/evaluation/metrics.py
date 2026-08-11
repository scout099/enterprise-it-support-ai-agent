"""Deterministic Phase 10 metrics with explicit denominators and N/A handling."""

import re
from collections.abc import Iterable

from enterprise_it_support.evaluation.dataset import EvaluationCase
from enterprise_it_support.evaluation.models import (
    AgentObservation,
    AggregateMetrics,
    CaseEvaluationResult,
    DeterministicCaseScores,
    MetricValue,
    SystemMetricSummary,
    TokenUsageObservation,
)

METRIC_DIRECTIONS: dict[str, str] = {
    "retrieval.recall_at_3": "higher",
    "retrieval.recall_at_5": "higher",
    "retrieval.mrr": "higher",
    "generation.citation_validity": "higher",
    "generation.evidence_coverage": "higher",
    "generation.unsupported_claim_rate": "lower",
    "generation.refusal_correctness": "higher",
    "agent.intent_accuracy": "higher",
    "agent.tool_selection_accuracy": "higher",
    "agent.tool_argument_accuracy": "higher",
    "agent.workflow_completion_rate": "higher",
    "agent.prohibited_action_rate": "lower",
    "system.latency_ms": "lower",
    "system.tool_error_rate": "lower",
    "system.average_steps": "lower",
    "system.average_total_tokens": "lower",
}


def evaluate_case(case: EvaluationCase, observation: AgentObservation) -> CaseEvaluationResult:
    """Compare one raw observation to its deterministic expected contract."""
    expected_titles = [document.title for document in case.expected_documents]
    rank = _first_expected_rank(observation.retrieved_document_titles, expected_titles)
    reciprocal_rank = None if not expected_titles else (0.0 if rank is None else 1.0 / rank)
    recall_at_3 = _recall_at_k(observation.retrieved_document_titles, expected_titles, 3)
    recall_at_5 = _recall_at_k(observation.retrieved_document_titles, expected_titles, 5)

    retrieved_chunks = set(observation.retrieved_chunk_ids)
    if observation.citation_chunk_ids:
        valid_citations = sum(
            chunk_id in retrieved_chunks for chunk_id in observation.citation_chunk_ids
        )
        citation_validity = valid_citations / len(observation.citation_chunk_ids)
    elif expected_titles:
        citation_validity = 0.0
    else:
        citation_validity = None

    evidence_coverage = (
        None
        if not expected_titles
        else len(set(expected_titles) & set(observation.citation_document_titles))
        / len(set(expected_titles))
    )
    unsupported_rate = _unsupported_claim_rate(
        observation.claims,
        observation.evidence_texts,
    )
    refusal_correctness = (
        None if observation.refused is None else observation.refused is case.expected_refusal
    )

    expected_tool_names = [tool.tool_name for tool in case.expected_tool_calls]
    actual_tool_names = [tool.tool_name for tool in observation.tool_calls]
    tool_selection = actual_tool_names == expected_tool_names
    tool_arguments = (
        None
        if not expected_tool_names and not actual_tool_names
        else tool_selection
        and all(
            actual.arguments == expected.arguments
            for actual, expected in zip(
                observation.tool_calls,
                case.expected_tool_calls,
                strict=True,
            )
        )
    )
    prohibited = bool(set(case.prohibited_actions) & set(observation.actual_actions))
    scores = DeterministicCaseScores(
        retrieval_rank=rank,
        recall_at_3=recall_at_3,
        recall_at_5=recall_at_5,
        reciprocal_rank=reciprocal_rank,
        citation_validity=citation_validity,
        evidence_coverage=evidence_coverage,
        unsupported_claim_rate=unsupported_rate,
        refusal_correctness=refusal_correctness,
        intent_accuracy=observation.actual_intent == case.expected_intent,
        tool_selection_accuracy=tool_selection,
        tool_argument_accuracy=tool_arguments,
        workflow_completion=observation.final_status == case.expected_final_status,
        prohibited_action=prohibited,
    )
    return CaseEvaluationResult(
        case_id=case.case_id,
        category=case.category,
        observation=observation,
        deterministic_scores=scores,
        failures=_failure_reasons(scores),
    )


def aggregate_metrics(results: Iterable[CaseEvaluationResult]) -> AggregateMetrics:
    """Aggregate all required metrics without turning missing samples into zero."""
    items = tuple(results)
    retrieval = {
        "recall_at_3": _optional_numeric_metric(
            item.deterministic_scores.recall_at_3 for item in items
        ),
        "recall_at_5": _optional_numeric_metric(
            item.deterministic_scores.recall_at_5 for item in items
        ),
        "mrr": _optional_numeric_metric(
            item.deterministic_scores.reciprocal_rank for item in items
        ),
    }
    generation = {
        "citation_validity": _optional_numeric_metric(
            item.deterministic_scores.citation_validity for item in items
        ),
        "evidence_coverage": _optional_numeric_metric(
            item.deterministic_scores.evidence_coverage for item in items
        ),
        "unsupported_claim_rate": _optional_numeric_metric(
            item.deterministic_scores.unsupported_claim_rate for item in items
        ),
        "refusal_correctness": _optional_boolean_metric(
            item.deterministic_scores.refusal_correctness for item in items
        ),
    }
    agent = {
        "intent_accuracy": _boolean_metric(
            item.deterministic_scores.intent_accuracy for item in items
        ),
        "tool_selection_accuracy": _boolean_metric(
            item.deterministic_scores.tool_selection_accuracy for item in items
        ),
        "tool_argument_accuracy": _optional_boolean_metric(
            item.deterministic_scores.tool_argument_accuracy for item in items
        ),
        "workflow_completion_rate": _boolean_metric(
            item.deterministic_scores.workflow_completion for item in items
        ),
        "prohibited_action_rate": _boolean_metric(
            item.deterministic_scores.prohibited_action for item in items
        ),
    }

    tool_calls = [tool for item in items for tool in item.observation.tool_calls]
    tokens = TokenUsageObservation(
        input_tokens=sum(item.observation.token_usage.input_tokens for item in items),
        output_tokens=sum(item.observation.token_usage.output_tokens for item in items),
        total_tokens=sum(item.observation.token_usage.total_tokens for item in items),
        cached_tokens=sum(item.observation.token_usage.cached_tokens for item in items),
        reasoning_tokens=sum(item.observation.token_usage.reasoning_tokens for item in items),
        model_calls=sum(item.observation.token_usage.model_calls for item in items),
    )
    system = SystemMetricSummary(
        latency_ms=_numeric_metric(item.observation.latency_ms for item in items),
        tool_error_rate=_boolean_metric(tool.status != "succeeded" for tool in tool_calls),
        average_steps=_numeric_metric(len(item.observation.steps) for item in items),
        token_usage=tokens,
        average_total_tokens=_numeric_metric(
            item.observation.token_usage.total_tokens for item in items
        ),
    )
    return AggregateMetrics(
        retrieval=retrieval,
        generation=generation,
        agent=agent,
        system=system,
    )


def _first_expected_rank(actual_titles: list[str], expected_titles: list[str]) -> int | None:
    if not expected_titles:
        return None
    expected = set(expected_titles)
    return next(
        (index for index, title in enumerate(actual_titles, start=1) if title in expected),
        None,
    )


def _recall_at_k(actual_titles: list[str], expected_titles: list[str], k: int) -> float | None:
    if not expected_titles:
        return None
    expected = set(expected_titles)
    retrieved = set(actual_titles[:k])
    return len(expected & retrieved) / len(expected)


def _unsupported_claim_rate(claims: list[str], evidence_texts: list[str]) -> float | None:
    if not claims:
        return None
    normalized_evidence = [_normalize(evidence) for evidence in evidence_texts if evidence.strip()]
    unsupported = 0
    for claim in claims:
        payload = _claim_payload(claim)
        normalized_claim = _normalize(payload)
        if not normalized_claim or not any(
            normalized_claim in evidence or _token_coverage(normalized_claim, evidence) >= 0.8
            for evidence in normalized_evidence
        ):
            unsupported += 1
    return unsupported / len(claims)


def _claim_payload(claim: str) -> str:
    prefixes = ("企业知识库片段说明:", "企业知识库:")
    normalized = claim.strip()
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix) :].strip()
    return normalized


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE))


def _token_coverage(claim: str, evidence: str) -> float:
    claim_tokens = set(claim.split())
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & set(evidence.split())) / len(claim_tokens)


def _failure_reasons(scores: DeterministicCaseScores) -> list[str]:
    failures = []
    if scores.recall_at_5 is not None and scores.recall_at_5 < 1:
        failures.append("expected_document_not_retrieved_at_5")
    if scores.citation_validity is not None and scores.citation_validity < 1:
        failures.append("citation_invalid")
    if scores.evidence_coverage is not None and scores.evidence_coverage < 1:
        failures.append("expected_evidence_not_cited")
    if scores.unsupported_claim_rate is not None and scores.unsupported_claim_rate > 0:
        failures.append("unsupported_claim_detected")
    if scores.refusal_correctness is False:
        failures.append("refusal_incorrect")
    if not scores.intent_accuracy:
        failures.append("intent_mismatch")
    if not scores.tool_selection_accuracy:
        failures.append("tool_selection_mismatch")
    elif scores.tool_argument_accuracy is False:
        failures.append("tool_argument_mismatch")
    if not scores.workflow_completion:
        failures.append("workflow_status_mismatch")
    if scores.prohibited_action:
        failures.append("prohibited_action_observed")
    return failures


def _boolean_metric(values: Iterable[bool]) -> MetricValue:
    items = tuple(values)
    numerator = float(sum(items))
    return MetricValue(
        value=(numerator / len(items) if items else None),
        sample_count=len(items),
        numerator=numerator,
    )


def _optional_boolean_metric(values: Iterable[bool | None]) -> MetricValue:
    return _boolean_metric(value for value in values if value is not None)


def _numeric_metric(values: Iterable[int | float]) -> MetricValue:
    items = tuple(float(value) for value in values)
    numerator = sum(items)
    return MetricValue(
        value=(numerator / len(items) if items else None),
        sample_count=len(items),
        numerator=numerator,
    )


def _optional_numeric_metric(values: Iterable[int | float | None]) -> MetricValue:
    return _numeric_metric(value for value in values if value is not None)
