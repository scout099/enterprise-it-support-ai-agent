"""CLI fail-closed tests that do not require PostgreSQL or external providers."""

from argparse import Namespace
from pathlib import Path

import pytest
from scripts.run_evaluations import run

from enterprise_it_support.platform.config import Settings


def _args(tmp_path: Path, **updates: object) -> Namespace:
    values = {
        "dataset": Path("data/evaluation/agent_cases.json"),
        "thresholds": Path("data/evaluation/thresholds.json"),
        "output_dir": tmp_path,
        "baseline": None,
        "no_seed_fixtures": False,
        "judge": False,
        "allow_real_api": False,
    }
    values.update(updates)
    return Namespace(**values)


def _fake_settings(**updates: object) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://demo:demo@localhost/evaluation",
        "embedding_provider": "fake",
        "model_provider": "fake",
    }
    values.update(updates)
    return Settings(**values)


async def test_cli_refuses_real_embedding_when_model_is_fake(tmp_path: Path) -> None:
    settings = _fake_settings(
        embedding_provider="openai",
        embedding_api_key="fictional-evaluation-key",
        embedding_model="embedding-demo",
        embedding_dimension=8,
        embedding_version="v1",
        rag_vector_threshold_profile="embedding-demo:8:v1",
    )

    with pytest.raises(ValueError, match="real model or embedding provider"):
        await run(_args(tmp_path), settings=settings)


async def test_explicit_missing_baseline_fails_instead_of_starting_over(tmp_path: Path) -> None:
    missing = tmp_path / "missing-baseline.json"

    with pytest.raises(ValueError, match="baseline does not exist"):
        await run(
            _args(tmp_path, baseline=missing),
            settings=_fake_settings(),
        )
