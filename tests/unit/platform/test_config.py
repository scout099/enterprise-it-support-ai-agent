"""Configuration behavior tests."""

import pytest

from enterprise_it_support.platform.config import (
    EmbeddingProviderType,
    Environment,
    ModelProviderType,
    Settings,
)

DEVELOPMENT_URL = "postgresql+psycopg://user:password@localhost:5432/app"
TEST_URL = "postgresql+psycopg://user:password@localhost:5432/app_test"


def test_development_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "development")
    monkeypatch.setenv("IT_SUPPORT_DEBUG", "true")
    monkeypatch.setenv("IT_SUPPORT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.active_database_url == DEVELOPMENT_URL


def test_test_environment_uses_separate_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_TEST_DATABASE_URL", TEST_URL)

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.TEST
    assert settings.active_database_url == TEST_URL


def test_test_environment_requires_separate_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.delenv("IT_SUPPORT_TEST_DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="test database URL"):
        Settings(_env_file=None)


def test_test_environment_rejects_development_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_TEST_DATABASE_URL", DEVELOPMENT_URL)

    with pytest.raises(ValueError, match="must differ"):
        Settings(_env_file=None)


def test_knowledge_chunking_configuration_loads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_KNOWLEDGE_CHUNK_SIZE", "240")
    monkeypatch.setenv("IT_SUPPORT_KNOWLEDGE_CHUNK_OVERLAP", "24")

    settings = Settings(_env_file=None)

    assert settings.knowledge_chunk_size == 240
    assert settings.knowledge_chunk_overlap == 24


def test_knowledge_chunk_overlap_must_be_smaller_than_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_KNOWLEDGE_CHUNK_SIZE", "20")
    monkeypatch.setenv("IT_SUPPORT_KNOWLEDGE_CHUNK_OVERLAP", "20")

    with pytest.raises(ValueError, match="overlap must be smaller"):
        Settings(_env_file=None)


def test_embedding_configuration_loads_model_dimension_version_and_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_DIMENSION", "256")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_VERSION", "support-v2")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_API_KEY", "test-secret-value")
    monkeypatch.setenv(
        "IT_SUPPORT_RAG_VECTOR_THRESHOLD_PROFILE",
        "text-embedding-3-small:256:support-v2",
    )

    settings = Settings(_env_file=None)

    assert settings.embedding_provider is EmbeddingProviderType.OPENAI
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimension == 256
    assert settings.embedding_version == "support-v2"
    assert settings.embedding_profile_key == "text-embedding-3-small:256:support-v2"
    assert settings.embedding_api_key is not None
    assert settings.embedding_api_key.get_secret_value() == "test-secret-value"


def test_openai_embedding_provider_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("IT_SUPPORT_EMBEDDING_API_KEY", raising=False)

    with pytest.raises(ValueError, match="API key"):
        Settings(_env_file=None)


def test_openai_vector_threshold_must_match_active_embedding_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_DIMENSION", "256")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_VERSION", "support-v2")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_API_KEY", "test-secret-value")
    monkeypatch.setenv(
        "IT_SUPPORT_RAG_VECTOR_THRESHOLD_PROFILE",
        "different-model:256:support-v2",
    )

    with pytest.raises(ValueError, match="bound to the active embedding profile"):
        Settings(_env_file=None)


def test_test_environment_forbids_external_embedding_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_TEST_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("IT_SUPPORT_EMBEDDING_API_KEY", "must-not-be-used")

    with pytest.raises(ValueError, match="test environment must use fake"):
        Settings(_env_file=None)


def test_model_gateway_configuration_loads_bounded_runtime_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("IT_SUPPORT_MODEL_NAME", "configured-chat-model")
    monkeypatch.setenv("IT_SUPPORT_MODEL_API_KEY", "test-model-secret")
    monkeypatch.setenv("IT_SUPPORT_MODEL_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("IT_SUPPORT_MODEL_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("IT_SUPPORT_MODEL_MAX_OUTPUT_TOKENS", "900")

    settings = Settings(_env_file=None)

    assert settings.model_provider is ModelProviderType.OPENAI
    assert settings.model_name == "configured-chat-model"
    assert settings.model_timeout_seconds == 12
    assert settings.model_max_attempts == 3
    assert settings.model_max_output_tokens == 900
    assert settings.model_api_key is not None
    assert settings.model_api_key.get_secret_value() == "test-model-secret"


def test_openai_model_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_MODEL_PROVIDER", "openai")
    monkeypatch.delenv("IT_SUPPORT_MODEL_API_KEY", raising=False)

    with pytest.raises(ValueError, match="model provider requires an API key"):
        Settings(_env_file=None)


def test_test_environment_forbids_external_model_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_ENVIRONMENT", "test")
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_TEST_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("IT_SUPPORT_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("IT_SUPPORT_MODEL_API_KEY", "must-not-be-used")

    with pytest.raises(ValueError, match="test environment must use fake model"):
        Settings(_env_file=None)


def test_agent_runtime_configuration_loads_bounded_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_AGENT_INTENT_CONFIDENCE_THRESHOLD", "0.7")
    monkeypatch.setenv("IT_SUPPORT_AGENT_MAX_NODES", "20")
    monkeypatch.setenv("IT_SUPPORT_AGENT_MAX_RETRIES", "2")
    monkeypatch.setenv("IT_SUPPORT_AGENT_MAX_TOOL_CALLS", "9")
    monkeypatch.setenv("IT_SUPPORT_AGENT_NODE_TIMEOUT_SECONDS", "8")
    monkeypatch.setenv("IT_SUPPORT_AGENT_TIMEOUT_SECONDS", "30")

    settings = Settings(_env_file=None)

    assert settings.agent_intent_confidence_threshold == 0.7
    assert settings.agent_max_nodes == 20
    assert settings.agent_max_retries == 2
    assert settings.agent_max_tool_calls == 9
    assert settings.agent_node_timeout_seconds == 8
    assert settings.agent_timeout_seconds == 30


def test_agent_total_timeout_must_exceed_node_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IT_SUPPORT_DATABASE_URL", DEVELOPMENT_URL)
    monkeypatch.setenv("IT_SUPPORT_AGENT_NODE_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("IT_SUPPORT_AGENT_TIMEOUT_SECONDS", "20")

    with pytest.raises(ValueError, match="greater than the per-node timeout"):
        Settings(_env_file=None)
