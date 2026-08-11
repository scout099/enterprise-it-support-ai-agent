"""Run the complete Phase 10 Agent evaluation and emit JSON plus Markdown reports."""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

import httpx
from apps.api.main import create_app
from apps.dependencies import build_model_gateway

from enterprise_it_support.conversation.repository import ConversationRepository
from enterprise_it_support.evaluation.dataset import (
    dataset_sha256,
    load_evaluation_dataset,
)
from enterprise_it_support.evaluation.fixtures import (
    EVALUATION_DOCUMENTS,
    EVALUATION_SOURCE_NAME,
    build_evaluation_retriever,
    seed_evaluation_fixtures,
)
from enterprise_it_support.evaluation.judge import ModelGatewayJudge
from enterprise_it_support.evaluation.reporting import (
    build_run_report,
    load_previous_report,
    load_thresholds,
    write_report_artifacts,
)
from enterprise_it_support.evaluation.runner import (
    LocalAgentEvaluationSubject,
    TrackingModelGateway,
    run_evaluation,
)
from enterprise_it_support.intelligence.model_gateway import FakeModelGateway
from enterprise_it_support.knowledge.domain import DocumentSummaryView
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.platform.config import (
    EmbeddingProviderType,
    ModelProviderType,
    Settings,
    get_settings,
)
from enterprise_it_support.platform.database import DatabaseManager
from enterprise_it_support.tools.persistence import ToolExecutionRepository

DEFAULT_DATASET = Path("data/evaluation/agent_cases.json")
DEFAULT_THRESHOLDS = Path("data/evaluation/thresholds.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/evaluations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Previous JSON report; defaults to OUTPUT_DIR/latest.json when it exists",
    )
    parser.add_argument(
        "--no-seed-fixtures",
        action="store_true",
        help="Do not idempotently import/index the six fictional evaluation documents",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Enable a separate advisory Judge; deterministic metrics remain authoritative",
    )
    parser.add_argument(
        "--allow-real-api",
        action="store_true",
        help="Explicitly allow configured non-Fake model calls for this evaluation",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace, *, settings: Settings | None = None) -> int:
    resolved_settings = settings or get_settings()
    root_logger = logging.getLogger()
    previous_handlers = [handler for handler in root_logger.handlers if _handler_is_open(handler)]
    previous_root_level = root_logger.level
    httpx_logger = logging.getLogger("httpx")
    previous_httpx_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    uses_real_model = resolved_settings.model_provider is not ModelProviderType.FAKE
    uses_real_embedding = resolved_settings.embedding_provider is not EmbeddingProviderType.FAKE
    if (uses_real_model or uses_real_embedding) and not args.allow_real_api:
        raise ValueError(
            "Evaluation refused a real model or embedding provider; pass --allow-real-api only "
            "with explicit data and budget authorization"
        )

    dataset = load_evaluation_dataset(args.dataset)
    thresholds = load_thresholds(args.thresholds)
    if args.baseline is not None and not args.baseline.exists():
        raise ValueError(f"Explicit evaluation baseline does not exist: {args.baseline}")
    baseline_path = args.baseline or args.output_dir / "latest.json"
    previous = load_previous_report(baseline_path)
    database = DatabaseManager(resolved_settings.active_database_url)
    if not args.no_seed_fixtures:
        await seed_evaluation_fixtures(resolved_settings, database)
    all_documents = await KnowledgeRepository(database.session_factory).list_documents()
    knowledge_documents = tuple(
        document for document in all_documents if document.source_name == EVALUATION_SOURCE_NAME
    )
    expected_corpus_size = len({title for _, title, _ in EVALUATION_DOCUMENTS})
    if len(knowledge_documents) != expected_corpus_size:
        raise ValueError(
            "Evaluation corpus is incomplete or ambiguous: "
            f"expected {expected_corpus_size} Documents, found {len(knowledge_documents)}"
        )
    corpus_fingerprint = _knowledge_corpus_fingerprint(knowledge_documents)
    evaluation_retriever = build_evaluation_retriever(
        resolved_settings,
        database,
        frozenset(document.id for document in knowledge_documents),
    )

    tracking_gateway = TrackingModelGateway(build_model_gateway(resolved_settings))
    conversations = ConversationRepository(database.session_factory)
    tools = ToolExecutionRepository(database.session_factory)
    try:
        app = create_app(
            settings=resolved_settings,
            database_manager=database,
            model_gateway=tracking_gateway,
            conversation_repository=conversations,
            tool_execution_repository=tools,
            knowledge_retriever=evaluation_retriever,
        )
        transport = httpx.ASGITransport(app=app)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://evaluation.local",
            ) as client:
                subject = LocalAgentEvaluationSubject(
                    client=client,
                    model_gateway=tracking_gateway,
                    conversation_repository=conversations,
                    tool_repository=tools,
                )
                judge = None
                if args.judge:
                    judge_gateway = (
                        FakeModelGateway(
                            [],
                            model_name=f"{resolved_settings.model_name}-judge",
                            response_factory=lambda _call: {
                                "score": 0.75,
                                "rationale_summary": (
                                    "Fake advisory Judge validates the separate scoring path only."
                                ),
                            },
                        )
                        if resolved_settings.model_provider is ModelProviderType.FAKE
                        else build_model_gateway(resolved_settings)
                    )
                    judge = ModelGatewayJudge(judge_gateway)
                execution = await run_evaluation(dataset, subject, judge=judge)
    finally:
        root_logger.handlers = previous_handlers
        root_logger.setLevel(previous_root_level)
        httpx_logger.setLevel(previous_httpx_level)

    report = build_run_report(
        dataset=dataset,
        dataset_digest=dataset_sha256(args.dataset),
        execution=execution,
        thresholds=thresholds,
        provider=resolved_settings.model_provider.value,
        configured_model=resolved_settings.model_name,
        embedding_provider=resolved_settings.embedding_provider.value,
        embedding_model=resolved_settings.embedding_model,
        embedding_profile=resolved_settings.embedding_profile_key,
        code_paths=(
            Path("apps/dependencies.py"),
            Path("src/enterprise_it_support/agent_runtime"),
            Path("src/enterprise_it_support/conversation"),
            Path("src/enterprise_it_support/evaluation"),
            Path("src/enterprise_it_support/governance"),
            Path("src/enterprise_it_support/intelligence"),
            Path("src/enterprise_it_support/knowledge"),
            Path("src/enterprise_it_support/service_desk"),
            Path("src/enterprise_it_support/tools"),
            args.dataset,
            args.thresholds,
        ),
        knowledge_corpus_fingerprint=corpus_fingerprint,
        knowledge_document_count=len(knowledge_documents),
        previous=previous,
    )
    paths = write_report_artifacts(report, args.output_dir)
    print(
        json.dumps(
            {
                "run_id": report.metadata.run_id,
                "dataset_version": report.metadata.dataset_version,
                "gate_passed": report.gate.passed,
                "failed_case_ids": report.failed_case_ids,
                "json_report": str(paths.json_path),
                "markdown_report": str(paths.markdown_path),
                "baseline_run_id": report.comparison.baseline_run_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report.gate.passed else 1


def _knowledge_corpus_fingerprint(documents: tuple[DocumentSummaryView, ...]) -> str:
    rows = [
        {
            "id": str(document.id),
            "source_name": document.source_name,
            "title": document.title,
            "status": document.status.value,
            "latest_version": document.latest_version,
        }
        for document in documents
    ]
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _handler_is_open(handler: logging.Handler) -> bool:
    stream = getattr(handler, "stream", None)
    return stream is None or not getattr(stream, "closed", False)


def main() -> None:
    try:
        exit_code = asyncio.run(run(parse_args()))
    except ValueError as exception:
        print(
            json.dumps(
                {
                    "error": "evaluation_configuration_error",
                    "message": str(exception),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
