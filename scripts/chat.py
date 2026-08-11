"""Simple terminal entry point for Phase 5 grounded chat."""

import argparse
import asyncio
import json
from uuid import UUID, uuid4

from apps.dependencies import build_knowledge_retriever, build_model_gateway

from enterprise_it_support.agent_runtime.rag import RAGAnswerService
from enterprise_it_support.conversation.repository import ConversationRepository
from enterprise_it_support.platform.config import Settings, get_settings
from enterprise_it_support.platform.database import DatabaseManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask grounded enterprise IT questions")
    parser.add_argument("--user-role", default="employee")
    parser.add_argument("--conversation-id", type=UUID)
    parser.add_argument("--question", help="Ask once and exit; omit for interactive mode")
    return parser


async def _ask_once(
    service: RAGAnswerService,
    *,
    question: str,
    user_role: str,
    conversation_id: UUID | None,
) -> UUID:
    turn = await service.ask(
        question=question,
        user_role=user_role,
        conversation_id=conversation_id,
        request_id=f"cli-{uuid4()}",
    )
    output = {
        "conversation_id": str(turn.conversation_id),
        **turn.answer.model_dump(mode="json"),
        "model_name": turn.model_metadata.resolved_model,
        "model_provider": turn.model_metadata.provider,
        "configured_model": turn.model_metadata.configured_model,
        "model_attempts": turn.model_metadata.attempts,
        "prompt_version": turn.model_metadata.prompt_version,
        "token_usage": turn.model_metadata.usage.__dict__,
        "latency_ms": turn.latency_ms,
        "request_id": turn.request_id,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return turn.conversation_id


async def run(args: argparse.Namespace, settings: Settings | None = None) -> int:
    resolved_settings = settings or get_settings()
    database = DatabaseManager(resolved_settings.active_database_url)
    try:
        service = RAGAnswerService(
            retriever=build_knowledge_retriever(
                resolved_settings,
                database.session_factory,
            ),
            model_gateway=build_model_gateway(resolved_settings),
            conversation_store=ConversationRepository(database.session_factory),
            top_k=resolved_settings.rag_top_k,
            max_context_chars=resolved_settings.rag_max_context_chars,
        )
        conversation_id = args.conversation_id
        if args.question is not None:
            await _ask_once(
                service,
                question=args.question,
                user_role=args.user_role,
                conversation_id=conversation_id,
            )
            return 0

        print("Grounded IT chat. Type 'exit' or 'quit' to stop.")
        while True:
            try:
                question = (await asyncio.to_thread(input, "you> ")).strip()
            except EOFError:
                print()
                break
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue
            conversation_id = await _ask_once(
                service,
                question=question,
                user_role=args.user_role,
                conversation_id=conversation_id,
            )
        return 0
    finally:
        await database.close()


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(run(args))
    except Exception as exception:
        print(
            json.dumps(
                {
                    "error": "chat_failed",
                    "error_type": type(exception).__name__,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
