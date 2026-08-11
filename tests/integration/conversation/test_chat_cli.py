"""One-shot grounded chat CLI integration test."""

import argparse
import asyncio
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from apps.api.main import create_app
from fastapi.testclient import TestClient
from scripts.chat import run
from sqlalchemy import create_engine, text

from enterprise_it_support.platform.config import Environment, Settings, get_settings

FIXTURES = Path(__file__).parents[3] / "data" / "evaluation" / "knowledge"


@pytest.mark.integration
def test_one_shot_cli_returns_grounded_answer_with_real_citation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    settings = Settings(environment=Environment.TEST).model_copy(
        update={
            "knowledge_storage_path": tmp_path,
            "knowledge_chunk_size": 40,
            "knowledge_chunk_overlap": 5,
        }
    )
    engine = create_engine(settings.active_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE messages, conversations, document_chunks, document_versions, "
                    "documents, knowledge_sources CASCADE"
                )
            )
    finally:
        engine.dispose()

    path = FIXTURES / "vpn_configuration_sop.md"
    with TestClient(create_app(settings=settings)) as client:
        upload = client.post(
            "/knowledge/documents",
            data={
                "title": "VPN CLI SOP",
                "owner": "Demo IT Team",
                "source_name": "CLI Library",
            },
            files={"file": (path.name, path.read_bytes(), "text/markdown")},
        )
        assert upload.status_code == 201
        indexed = client.post(f"/knowledge/documents/{upload.json()['document_id']}/index")
        assert indexed.status_code == 200

    args = argparse.Namespace(
        user_role="employee",
        conversation_id=None,
        question="Which VPN server should I use?",
    )
    exit_code = asyncio.run(run(args, settings))
    captured = capsys.readouterr().out
    answer_start = captured.rfind('{\n  "conversation_id"')
    output = json.loads(captured[answer_start:])

    assert exit_code == 0
    assert output["summary"]
    assert output["citations"][0]["document_title"] == "VPN CLI SOP"
    assert output["citations"][0]["chunk_id"]
    assert output["prompt_version"] == "rag-answer-v1"
    assert output["model_name"] == "fake-chat-v1"
