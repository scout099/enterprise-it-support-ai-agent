"""Run the Phase 5 retrieval/relevance dataset and print deterministic gate metrics."""

import argparse
import asyncio
import json
from pathlib import Path

from apps.dependencies import build_knowledge_retriever, build_relevance_policy

from enterprise_it_support.evaluation.fixtures import seed_evaluation_fixtures
from enterprise_it_support.evaluation.retrieval import (
    evaluate_retrieval,
    load_retrieval_dataset,
    resolve_expected_documents,
)
from enterprise_it_support.knowledge.repository import KnowledgeRepository
from enterprise_it_support.platform.config import Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager

DEFAULT_DATASET = Path("data/evaluation/retrieval_cases.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--user-role", default="employee")
    parser.add_argument(
        "--seed-fixtures",
        action="store_true",
        help="Idempotently import and index the six fictional evaluation documents first",
    )
    return parser.parse_args()


async def run(
    args: argparse.Namespace,
    *,
    settings: Settings | None = None,
) -> int:
    resolved_settings = settings or get_settings()
    database = DatabaseManager(resolved_settings.active_database_url)
    try:
        if args.seed_fixtures:
            await seed_evaluation_fixtures(resolved_settings, database)
        dataset_version, cases = load_retrieval_dataset(args.dataset)
        documents = await KnowledgeRepository(database.session_factory).list_documents()
        resolved_cases = resolve_expected_documents(cases, documents)
        retriever = build_knowledge_retriever(resolved_settings, database.session_factory)
        report = await evaluate_retrieval(
            retriever,
            dataset_version=dataset_version,
            cases=resolved_cases,
            user_role=args.user_role,
            relevance_policy=build_relevance_policy(resolved_settings),
        )
        print(
            json.dumps(
                {
                    "dataset_version": report.dataset_version,
                    "total_cases": report.total_cases,
                    "positive_cases": report.positive_cases,
                    "negative_cases": report.negative_cases,
                    "recall_at_3": report.recall_at_3,
                    "recall_at_5": report.recall_at_5,
                    "false_answer_rate": report.false_answer_rate,
                    "false_answer_rate_scope": "relevance_gate_proxy",
                    "abstention_accuracy": report.abstention_accuracy,
                    "missed_at_3": report.missed_at_3,
                    "missed_at_5": report.missed_at_5,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    finally:
        await database.close()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
