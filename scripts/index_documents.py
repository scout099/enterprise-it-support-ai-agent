"""Index pending knowledge document chunks with the configured Provider."""

import argparse
import asyncio
import json
from dataclasses import asdict
from uuid import UUID

from apps.dependencies import build_indexing_service

from enterprise_it_support.knowledge.indexing import IndexingDocumentNotFoundError
from enterprise_it_support.platform.config import Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager
from enterprise_it_support.platform.logging import configure_logging


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI controls without accessing configuration or the database."""
    parser = argparse.ArgumentParser(description="Index enterprise IT knowledge chunks")
    parser.add_argument("--document-id", type=UUID, help="Index one logical Document")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute current embeddings for the specified Document",
    )
    args = parser.parse_args(arguments)
    if args.force and args.document_id is None:
        parser.error("--force requires --document-id")
    return args


async def run(args: argparse.Namespace, *, settings: Settings | None = None) -> int:
    """Execute indexing and return a process exit code."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    database = DatabaseManager(resolved_settings.active_database_url)
    service = build_indexing_service(resolved_settings, database.session_factory)
    try:
        if args.document_id is not None:
            try:
                results = (await service.index_document(args.document_id, force=args.force),)
            except IndexingDocumentNotFoundError as exception:
                print(json.dumps({"error": str(exception)}))
                return 2
        else:
            results = await service.index_pending_documents()
    finally:
        await database.close()

    payload = {
        "documents": [asdict(result) for result in results],
        "document_count": len(results),
        "indexed_chunks": sum(result.indexed_chunks for result in results),
        "skipped_chunks": sum(result.skipped_chunks for result in results),
        "failed_chunks": sum(result.failed_chunks for result in results),
    }
    print(json.dumps(payload, default=str))
    return 1 if payload["failed_chunks"] else 0


def main(arguments: list[str] | None = None) -> None:
    """Synchronous module entry point."""
    raise SystemExit(asyncio.run(run(parse_args(arguments))))


if __name__ == "__main__":
    main()
