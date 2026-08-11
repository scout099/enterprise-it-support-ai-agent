"""Regression gates, previous-run comparison, and report artifact rendering."""

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from enterprise_it_support.evaluation.dataset import EvaluationDataset
from enterprise_it_support.evaluation.metrics import METRIC_DIRECTIONS
from enterprise_it_support.evaluation.models import (
    AggregateMetrics,
    CaseEvaluationResult,
    MetricValue,
)
from enterprise_it_support.evaluation.runner import EvaluationExecution

WORKFLOW_VERSION = "agent-workflow-phase-10-v1"


class ThresholdRule(BaseModel):
    """One inclusive minimum or maximum regression threshold."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def require_exactly_one_bound(self) -> "ThresholdRule":
        if (self.minimum is None) is (self.maximum is None):
            raise ValueError("Threshold rule must declare exactly one bound")
        return self


class ThresholdConfig(BaseModel):
    """Versioned quality and safety gate configuration."""

    model_config = ConfigDict(extra="forbid")

    threshold_version: str
    rules: list[ThresholdRule]
    safety_regression_metrics: list[str]


class GateFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    reason: str
    observed: float | None
    required: float | None


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    threshold_version: str
    failures: list[GateFailure]


class MetricDifference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    previous: float | None
    current: float | None
    delta: float | None
    change: Literal["improved", "regressed", "unchanged", "not_comparable"]


class RunComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str | None
    differences: list[MetricDifference]
    is_comparable: bool = True
    not_comparable_reasons: list[str] = Field(default_factory=list)


class EvaluationRunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: datetime
    dataset_version: str
    dataset_sha256: str
    workflow_version: str
    code_fingerprint: str
    knowledge_corpus_fingerprint: str = "unknown"
    knowledge_document_count: int = 0
    git_commit: str | None
    provider: str
    configured_model: str
    embedding_provider: str = "unknown"
    embedding_model: str = "unknown"
    embedding_profile: str = "unknown"
    prompt_versions: list[str]
    judge_enabled: bool
    judge_is_advisory: bool = True


class EvaluationRunReport(BaseModel):
    """Self-contained JSON artifact used for reports and future comparisons."""

    model_config = ConfigDict(extra="forbid")

    metadata: EvaluationRunMetadata
    metrics: AggregateMetrics
    category_metrics: dict[str, AggregateMetrics]
    cases: list[CaseEvaluationResult]
    failed_case_ids: list[str]
    judge_results: list[dict[str, object]]
    gate: GateResult
    comparison: RunComparison
    limitations: list[str]


class ReportPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    json_path: Path
    markdown_path: Path
    latest_json_path: Path
    latest_markdown_path: Path


def load_thresholds(path: Path) -> ThresholdConfig:
    """Load strict regression thresholds from a versioned JSON artifact."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise ValueError(f"Unable to load evaluation thresholds: {path}") from exception
    return ThresholdConfig.model_validate(raw)


def load_previous_report(path: Path | None) -> EvaluationRunReport | None:
    if path is None or not path.exists():
        return None
    try:
        return EvaluationRunReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exception:
        raise ValueError(f"Unable to load previous evaluation report: {path}") from exception


def build_run_report(
    *,
    dataset: EvaluationDataset,
    dataset_digest: str,
    execution: EvaluationExecution,
    thresholds: ThresholdConfig,
    provider: str,
    configured_model: str,
    embedding_provider: str = "unknown",
    embedding_model: str = "unknown",
    embedding_profile: str = "unknown",
    code_paths: tuple[Path, ...],
    knowledge_corpus_fingerprint: str,
    knowledge_document_count: int,
    previous: EvaluationRunReport | None,
) -> EvaluationRunReport:
    """Attach version identity, comparison, and regression gates to raw execution data."""
    prompt_versions = sorted(
        {version for result in execution.cases for version in result.observation.prompt_versions}
    )
    metadata = EvaluationRunMetadata(
        run_id=f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset_digest,
        workflow_version=WORKFLOW_VERSION,
        code_fingerprint=code_fingerprint(code_paths),
        knowledge_corpus_fingerprint=knowledge_corpus_fingerprint,
        knowledge_document_count=knowledge_document_count,
        git_commit=read_git_commit(Path(".git")),
        provider=provider,
        configured_model=configured_model,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_profile=embedding_profile,
        prompt_versions=prompt_versions,
        judge_enabled=bool(execution.judge_results),
    )
    not_comparable_reasons = []
    if previous is not None and previous.metadata.dataset_sha256 != dataset_digest:
        not_comparable_reasons.append("dataset_sha256_changed")
    if (
        previous is not None
        and previous.metadata.knowledge_corpus_fingerprint != knowledge_corpus_fingerprint
    ):
        not_comparable_reasons.append("knowledge_corpus_fingerprint_changed")
    comparison = compare_metrics(
        execution.metrics,
        None if previous is None else previous.metrics,
        baseline_run_id=None if previous is None else previous.metadata.run_id,
        not_comparable_reasons=tuple(not_comparable_reasons),
    )
    gate = evaluate_gate(execution.metrics, thresholds, comparison, cases=execution.cases)
    return EvaluationRunReport(
        metadata=metadata,
        metrics=execution.metrics,
        category_metrics=execution.category_metrics,
        cases=list(execution.cases),
        failed_case_ids=[result.case_id for result in execution.cases if result.failures],
        judge_results=[result.model_dump(mode="json") for result in execution.judge_results],
        gate=gate,
        comparison=comparison,
        limitations=[
            "Unsupported Claim Rate is a deterministic lexical support rule, "
            "not semantic entailment.",
            "Latency depends on the local machine and PostgreSQL state.",
            "Fake provider scores validate orchestration deterministically, "
            "not real-model quality.",
            "Optional Judge scores are advisory and never override deterministic gates.",
        ],
    )


def compare_metrics(
    current: AggregateMetrics,
    previous: AggregateMetrics | None,
    *,
    baseline_run_id: str | None,
    not_comparable_reasons: tuple[str, ...] = (),
) -> RunComparison:
    current_values = flatten_metrics(current)
    previous_values = {} if previous is None else flatten_metrics(previous)
    differences = []
    for name in sorted(current_values):
        current_value = current_values[name].value
        previous_value = previous_values.get(name, MetricValue(value=None, sample_count=0)).value
        if not_comparable_reasons or current_value is None or previous_value is None:
            delta = None
            change: Literal["improved", "regressed", "unchanged", "not_comparable"] = (
                "not_comparable"
            )
        else:
            delta = current_value - previous_value
            if abs(delta) < 1e-12:
                change = "unchanged"
            elif METRIC_DIRECTIONS.get(name, "higher") == "higher":
                change = "improved" if delta > 0 else "regressed"
            else:
                change = "improved" if delta < 0 else "regressed"
        differences.append(
            MetricDifference(
                metric=name,
                previous=previous_value,
                current=current_value,
                delta=delta,
                change=change,
            )
        )
    return RunComparison(
        baseline_run_id=baseline_run_id,
        differences=differences,
        is_comparable=not not_comparable_reasons,
        not_comparable_reasons=list(not_comparable_reasons),
    )


def evaluate_gate(
    metrics: AggregateMetrics,
    thresholds: ThresholdConfig,
    comparison: RunComparison,
    *,
    cases: Sequence[CaseEvaluationResult] = (),
) -> GateResult:
    """Fail on configured thresholds and any comparable safety regression."""
    values = flatten_metrics(metrics)
    failures = []
    for rule in thresholds.rules:
        observed = values.get(rule.metric)
        value = None if observed is None else observed.value
        if value is None:
            failures.append(
                GateFailure(
                    metric=rule.metric,
                    reason="metric_has_no_applicable_samples",
                    observed=None,
                    required=rule.minimum if rule.minimum is not None else rule.maximum,
                )
            )
        elif rule.minimum is not None and value < rule.minimum:
            failures.append(
                GateFailure(
                    metric=rule.metric,
                    reason="below_minimum",
                    observed=value,
                    required=rule.minimum,
                )
            )
        elif rule.maximum is not None and value > rule.maximum:
            failures.append(
                GateFailure(
                    metric=rule.metric,
                    reason="above_maximum",
                    observed=value,
                    required=rule.maximum,
                )
            )

    differences = {item.metric: item for item in comparison.differences}
    for metric in thresholds.safety_regression_metrics:
        difference = differences.get(metric)
        if difference is not None and difference.change == "regressed":
            failures.append(
                GateFailure(
                    metric=metric,
                    reason="safety_metric_regressed_from_previous_run",
                    observed=difference.current,
                    required=difference.previous,
                )
            )
    execution_failures = [
        case for case in cases if case.observation.final_status.startswith("http_error_")
    ]
    if execution_failures:
        completed = len(cases) - len(execution_failures)
        failures.append(
            GateFailure(
                metric="system.evaluation_completion_rate",
                reason="evaluation_case_http_error",
                observed=completed / len(cases),
                required=1.0,
            )
        )
    return GateResult(
        passed=not failures,
        threshold_version=thresholds.threshold_version,
        failures=failures,
    )


def write_report_artifacts(report: EvaluationRunReport, output_dir: Path) -> ReportPaths:
    """Write immutable run artifacts plus convenient latest aliases."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{report.metadata.run_id}.json"
    markdown_path = output_dir / f"{report.metadata.run_id}.md"
    latest_json = output_dir / "latest.json"
    latest_markdown = output_dir / "latest.md"
    json_content = report.model_dump_json(indent=2)
    markdown_content = render_markdown_report(report)
    json_path.write_text(json_content + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_content, encoding="utf-8")
    if report.gate.passed:
        latest_json.write_text(json_content + "\n", encoding="utf-8")
        latest_markdown.write_text(markdown_content, encoding="utf-8")
    return ReportPaths(
        json_path=json_path,
        markdown_path=markdown_path,
        latest_json_path=latest_json,
        latest_markdown_path=latest_markdown,
    )


def render_markdown_report(report: EvaluationRunReport) -> str:
    """Render a project-report-ready Markdown summary from the raw JSON model."""
    lines = [
        "# Agent Evaluation Report",
        "",
        f"- Run: `{report.metadata.run_id}`",
        f"- Dataset: `{report.metadata.dataset_version}`",
        f"- Provider/model: `{report.metadata.provider}` / `{report.metadata.configured_model}`",
        f"- Embedding: `{report.metadata.embedding_provider}` / "
        f"`{report.metadata.embedding_profile}`",
        f"- Gate: **{'PASS' if report.gate.passed else 'FAIL'}**",
        f"- Previous run: `{report.comparison.baseline_run_id or 'none'}`",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value | Samples |",
        "| --- | ---: | ---: |",
    ]
    for name, metric in flatten_metrics(report.metrics).items():
        lines.append(f"| {name} | {_format_metric(metric.value)} | {metric.sample_count} |")

    lines.extend(
        [
            "",
            "## Category summary",
            "",
            "| Category | Cases | Intent | Workflow | Prohibited action |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for category, metrics in sorted(report.category_metrics.items()):
        intent = metrics.agent["intent_accuracy"]
        workflow = metrics.agent["workflow_completion_rate"]
        prohibited = metrics.agent["prohibited_action_rate"]
        lines.append(
            f"| {category} | {intent.sample_count} | {_format_metric(intent.value)} | "
            f"{_format_metric(workflow.value)} | {_format_metric(prohibited.value)} |"
        )

    lines.extend(["", "## Failed cases", ""])
    if not report.failed_case_ids:
        lines.append("No deterministic case failures.")
    else:
        for result in report.cases:
            if result.failures:
                lines.append(f"- `{result.case_id}`: {', '.join(result.failures)}")

    lines.extend(["", "## Difference from previous run", ""])
    if report.comparison.baseline_run_id is None:
        lines.append("No previous run was available; this artifact establishes the baseline.")
    elif not report.comparison.is_comparable:
        reasons = ", ".join(report.comparison.not_comparable_reasons)
        lines.append(f"Previous run is not comparable: {reasons}.")
    else:
        lines.extend(
            [
                "| Metric | Previous | Current | Delta | Change |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for difference in report.comparison.differences:
            lines.append(
                f"| {difference.metric} | {_format_metric(difference.previous)} | "
                f"{_format_metric(difference.current)} | {_format_metric(difference.delta)} | "
                f"{difference.change} |"
            )

    lines.extend(["", "## Regression gate", ""])
    if report.gate.passed:
        lines.append("All configured thresholds and comparable safety regressions passed.")
    else:
        for failure in report.gate.failures:
            lines.append(
                f"- `{failure.metric}`: {failure.reason}; observed="
                f"{_format_metric(failure.observed)}, required={_format_metric(failure.required)}"
            )

    if report.judge_results:
        lines.extend(
            [
                "",
                "## Optional advisory Judge",
                "",
                "Judge results are reported separately and are not treated as ground truth.",
            ]
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    return "\n".join(lines) + "\n"


def flatten_metrics(metrics: AggregateMetrics) -> dict[str, MetricValue]:
    return {
        **{f"retrieval.{name}": value for name, value in metrics.retrieval.items()},
        **{f"generation.{name}": value for name, value in metrics.generation.items()},
        **{f"agent.{name}": value for name, value in metrics.agent.items()},
        "system.latency_ms": metrics.system.latency_ms,
        "system.tool_error_rate": metrics.system.tool_error_rate,
        "system.average_steps": metrics.system.average_steps,
        "system.average_total_tokens": metrics.system.average_total_tokens,
    }


def code_fingerprint(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(candidate for candidate in path.rglob("*.py") if candidate.is_file())
        elif path.is_file():
            files.append(path)
    for path in sorted(files):
        digest.update(str(path).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_git_commit(git_dir: Path) -> str | None:
    """Read the current loose Git ref without invoking a shell."""
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref: "):
            return head or None
        ref_path = git_dir / head.removeprefix("ref: ")
        return ref_path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"
