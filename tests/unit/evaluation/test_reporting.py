"""Report, diff, and safety regression gate tests."""

from pathlib import Path

from enterprise_it_support.evaluation.dataset import (
    dataset_sha256,
    load_evaluation_dataset,
)
from enterprise_it_support.evaluation.models import (
    AggregateMetrics,
    MetricValue,
    SystemMetricSummary,
    TokenUsageObservation,
)
from enterprise_it_support.evaluation.reporting import (
    GateFailure,
    GateResult,
    build_run_report,
    compare_metrics,
    evaluate_gate,
    load_previous_report,
    load_thresholds,
    write_report_artifacts,
)
from enterprise_it_support.evaluation.runner import run_evaluation
from tests.unit.evaluation.test_agent_runner import PerfectFakeSubject


async def test_report_writes_raw_json_markdown_categories_and_failure_list(
    tmp_path: Path,
) -> None:
    dataset_path = Path("data/evaluation/agent_cases.json")
    dataset = load_evaluation_dataset(dataset_path)
    execution = await run_evaluation(dataset, PerfectFakeSubject())
    thresholds = load_thresholds(Path("data/evaluation/thresholds.json"))

    report = build_run_report(
        dataset=dataset,
        dataset_digest=dataset_sha256(dataset_path),
        execution=execution,
        thresholds=thresholds,
        provider="fake",
        configured_model="fake-chat-v1",
        code_paths=(Path("src/enterprise_it_support/evaluation"),),
        knowledge_corpus_fingerprint="corpus-v1",
        knowledge_document_count=6,
        previous=None,
    )
    paths = write_report_artifacts(report, tmp_path)
    loaded = load_previous_report(paths.json_path)

    assert report.gate.passed is True
    assert report.comparison.baseline_run_id is None
    assert loaded is not None
    assert loaded.metadata.run_id == report.metadata.run_id
    assert paths.latest_json_path.exists()
    markdown = paths.markdown_path.read_text(encoding="utf-8")
    assert "## Category summary" in markdown
    assert "## Failed cases" in markdown
    assert "## Difference from previous run" in markdown
    assert "## Regression gate" in markdown


async def test_failed_report_keeps_last_passing_latest_baseline(tmp_path: Path) -> None:
    dataset_path = Path("data/evaluation/agent_cases.json")
    dataset = load_evaluation_dataset(dataset_path)
    execution = await run_evaluation(dataset, PerfectFakeSubject())
    passing = build_run_report(
        dataset=dataset,
        dataset_digest=dataset_sha256(dataset_path),
        execution=execution,
        thresholds=load_thresholds(Path("data/evaluation/thresholds.json")),
        provider="fake",
        configured_model="fake-chat-v1",
        code_paths=(Path("src/enterprise_it_support/evaluation"),),
        knowledge_corpus_fingerprint="corpus-v1",
        knowledge_document_count=6,
        previous=None,
    )
    write_report_artifacts(passing, tmp_path)
    failing = passing.model_copy(
        deep=True,
        update={
            "metadata": passing.metadata.model_copy(update={"run_id": "eval-failing"}),
            "gate": GateResult(
                passed=False,
                threshold_version="phase-10-v1",
                failures=[
                    GateFailure(
                        metric="agent.prohibited_action_rate",
                        reason="above_maximum",
                        observed=0.1,
                        required=0.0,
                    )
                ],
            ),
        },
    )

    failed_paths = write_report_artifacts(failing, tmp_path)
    latest = load_previous_report(tmp_path / "latest.json")

    assert failed_paths.json_path.exists()
    assert latest is not None
    assert latest.metadata.run_id == passing.metadata.run_id


async def test_changed_dataset_or_corpus_is_reported_as_not_comparable() -> None:
    dataset_path = Path("data/evaluation/agent_cases.json")
    dataset = load_evaluation_dataset(dataset_path)
    execution = await run_evaluation(dataset, PerfectFakeSubject())
    thresholds = load_thresholds(Path("data/evaluation/thresholds.json"))
    previous = build_run_report(
        dataset=dataset,
        dataset_digest="old-dataset",
        execution=execution,
        thresholds=thresholds,
        provider="fake",
        configured_model="fake-chat-v1",
        code_paths=(Path("src/enterprise_it_support/evaluation"),),
        knowledge_corpus_fingerprint="old-corpus",
        knowledge_document_count=6,
        previous=None,
    )

    current = build_run_report(
        dataset=dataset,
        dataset_digest=dataset_sha256(dataset_path),
        execution=execution,
        thresholds=thresholds,
        provider="fake",
        configured_model="fake-chat-v1",
        code_paths=(Path("src/enterprise_it_support/evaluation"),),
        knowledge_corpus_fingerprint="new-corpus",
        knowledge_document_count=6,
        previous=previous,
    )

    assert current.comparison.is_comparable is False
    assert current.comparison.not_comparable_reasons == [
        "dataset_sha256_changed",
        "knowledge_corpus_fingerprint_changed",
    ]
    assert all(item.change == "not_comparable" for item in current.comparison.differences)


async def test_http_case_failures_cannot_pass_at_inclusive_quality_threshold() -> None:
    dataset = load_evaluation_dataset(Path("data/evaluation/agent_cases.json"))
    execution = await run_evaluation(dataset, PerfectFakeSubject())
    cases = list(execution.cases)
    for index in range(3):
        cases[index] = cases[index].model_copy(
            deep=True,
            update={
                "observation": cases[index].observation.model_copy(
                    update={"final_status": "http_error_503"}
                )
            },
        )
    metrics = execution.metrics.model_copy(deep=True)
    metrics.agent["intent_accuracy"] = metrics.agent["intent_accuracy"].model_copy(
        update={"value": 0.9, "numerator": 27.0}
    )
    metrics.agent["workflow_completion_rate"] = metrics.agent[
        "workflow_completion_rate"
    ].model_copy(update={"value": 0.9, "numerator": 27.0})
    comparison = compare_metrics(metrics, None, baseline_run_id=None)

    gate = evaluate_gate(
        metrics,
        load_thresholds(Path("data/evaluation/thresholds.json")),
        comparison,
        cases=cases,
    )

    assert gate.passed is False
    assert any(failure.reason == "evaluation_case_http_error" for failure in gate.failures)


async def test_threshold_and_previous_safety_regression_fail_the_gate() -> None:
    dataset = load_evaluation_dataset(Path("data/evaluation/agent_cases.json"))
    execution = await run_evaluation(dataset, PerfectFakeSubject())
    thresholds = load_thresholds(Path("data/evaluation/thresholds.json"))
    current = execution.metrics.model_copy(deep=True)
    current.agent["intent_accuracy"] = current.agent["intent_accuracy"].model_copy(
        update={"value": 0.89}
    )
    current.agent["prohibited_action_rate"] = current.agent["prohibited_action_rate"].model_copy(
        update={"value": 0.1}
    )
    comparison = compare_metrics(current, execution.metrics, baseline_run_id="baseline")

    gate = evaluate_gate(current, thresholds, comparison)

    assert gate.passed is False
    reasons = {(failure.metric, failure.reason) for failure in gate.failures}
    assert ("agent.intent_accuracy", "below_minimum") in reasons
    assert ("agent.prohibited_action_rate", "above_maximum") in reasons
    assert (
        "agent.prohibited_action_rate",
        "safety_metric_regressed_from_previous_run",
    ) in reasons


def test_comparison_marks_lower_is_better_metric_correctly() -> None:
    current = _minimal_metrics(prohibited_rate=0.0)
    previous = _minimal_metrics(prohibited_rate=0.2)

    comparison = compare_metrics(current, previous, baseline_run_id="previous")
    difference = next(
        item for item in comparison.differences if item.metric == "agent.prohibited_action_rate"
    )

    assert difference.delta == -0.2
    assert difference.change == "improved"


def _minimal_metrics(*, prohibited_rate: float) -> AggregateMetrics:
    value = MetricValue(value=1.0, sample_count=1, numerator=1.0)
    return AggregateMetrics(
        retrieval={"recall_at_3": value, "recall_at_5": value, "mrr": value},
        generation={
            "citation_validity": value,
            "evidence_coverage": value,
            "unsupported_claim_rate": MetricValue(value=0.0, sample_count=1),
            "refusal_correctness": value,
        },
        agent={
            "intent_accuracy": value,
            "tool_selection_accuracy": value,
            "tool_argument_accuracy": value,
            "workflow_completion_rate": value,
            "prohibited_action_rate": MetricValue(
                value=prohibited_rate,
                sample_count=1,
                numerator=prohibited_rate,
            ),
        },
        system=SystemMetricSummary(
            latency_ms=value,
            tool_error_rate=MetricValue(value=0.0, sample_count=1),
            average_steps=value,
            token_usage=TokenUsageObservation(),
            average_total_tokens=value,
        ),
    )
