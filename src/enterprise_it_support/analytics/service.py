"""Backend-owned pandas projections for SQL aggregates and Evaluation artifacts."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from enterprise_it_support.analytics.persistence import AnalyticsRepository
from enterprise_it_support.analytics.schemas import (
    AnalyticsSummaryResponse,
    CountItemResponse,
    EvaluationSummaryResponse,
    MetricResponse,
)


class AnalyticsService:
    """Combine bounded SQL aggregates with local Evaluation report projections."""

    def __init__(
        self,
        repository: AnalyticsRepository,
        evaluation_artifacts_path: Path,
    ) -> None:
        self._repository = repository
        self._evaluation_artifacts_path = evaluation_artifacts_path

    async def summary(
        self,
        *,
        days: int,
        evaluation_limit: int,
        now: datetime | None = None,
    ) -> AnalyticsSummaryResponse:
        end = now or datetime.now(UTC)
        start = end - timedelta(days=days)
        raw = await self._repository.load(start=start, end=end)
        values = raw.summary
        total_runs = int(values["total_agent_runs"] or 0)
        feedback_count = int(values["feedback_count"] or 0)
        tool_count = int(values["tool_count"] or 0)
        satisfaction_samples = int(values["satisfaction_samples"] or 0)
        return AnalyticsSummaryResponse(
            window_start=start,
            window_end=end,
            total_agent_runs=total_runs,
            total_tickets=int(values["total_tickets"] or 0),
            ticket_categories=_count_items(raw.ticket_categories),
            issue_counts=_count_items(
                raw.issue_counts,
                labels={
                    "vpn_diagnosis": "VPN",
                    "outlook_diagnosis": "Outlook",
                    "account_diagnosis": "Account",
                },
            ),
            self_service_resolution_rate=_ratio(
                values["self_service_resolved"],
                feedback_count,
            ),
            human_transfer_rate=_ratio(values["transferred_runs"], total_runs),
            average_agent_steps=_average(values["average_agent_steps"], total_runs),
            average_tool_calls=_average(values["average_tool_calls"], total_runs),
            average_response_time_ms=_average(
                values["average_response_time_ms"],
                int(values["response_time_samples"] or 0),
            ),
            tool_success_rate=_ratio(values["successful_tools"], tool_count),
            average_satisfaction=_average(
                values["average_satisfaction"],
                satisfaction_samples,
            ),
            satisfaction_distribution=_count_items(raw.satisfaction_distribution),
            frequent_failure_reasons=_count_items(raw.failure_reasons),
            recent_evaluations=_load_evaluations(
                self._evaluation_artifacts_path,
                evaluation_limit,
            ),
        )


def _ratio(numerator: Any, denominator: int) -> MetricResponse:
    if denominator == 0:
        return MetricResponse(value=None, sample_count=0)
    return MetricResponse(value=float(numerator or 0) / denominator, sample_count=denominator)


def _average(value: Any, sample_count: int) -> MetricResponse:
    if sample_count == 0 or value is None or pd.isna(value):
        return MetricResponse(value=None, sample_count=0)
    return MetricResponse(value=float(value), sample_count=sample_count)


def _count_items(
    rows: tuple[dict[str, Any], ...],
    labels: dict[str, str] | None = None,
) -> list[CountItemResponse]:
    if not rows:
        return []
    frame = pd.DataFrame.from_records(rows, columns=["label", "count"])
    if labels is not None:
        frame["label"] = frame["label"].replace(labels)
    frame["count"] = frame["count"].astype(int)
    frame = frame.sort_values(["count", "label"], ascending=[False, True])
    return [
        CountItemResponse(label=str(row.label), count=int(row.count))
        for row in frame.itertuples(index=False)
    ]


def _load_evaluations(path: Path, limit: int) -> list[EvaluationSummaryResponse]:
    records: dict[str, EvaluationSummaryResponse] = {}
    for report_path in path.glob("eval-*.json") if path.exists() else ():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            metadata = payload["metadata"]
            metrics = payload["metrics"]
            run_id = str(metadata["run_id"])
            records[run_id] = EvaluationSummaryResponse(
                run_id=run_id,
                created_at=metadata["created_at"],
                gate_passed=bool(payload["gate"]["passed"]),
                dataset_version=str(metadata["dataset_version"]),
                intent_accuracy=_metric_value(metrics, "agent", "intent_accuracy"),
                workflow_completion_rate=_metric_value(
                    metrics,
                    "agent",
                    "workflow_completion_rate",
                ),
                citation_validity=_metric_value(metrics, "generation", "citation_validity"),
                failed_case_count=len(payload.get("failed_case_ids", [])),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            continue
    return sorted(records.values(), key=lambda item: item.created_at, reverse=True)[:limit]


def _metric_value(payload: dict[str, Any], group: str, metric: str) -> float | None:
    value = payload[group][metric]["value"]
    return None if value is None else float(value)
