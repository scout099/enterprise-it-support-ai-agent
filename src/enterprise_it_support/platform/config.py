"""Environment-backed application configuration."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported runtime configuration profiles."""

    DEVELOPMENT = "development"
    TEST = "test"


class EmbeddingProviderType(StrEnum):
    """Embedding adapters available at the application boundary."""

    FAKE = "fake"
    OPENAI = "openai"


class ModelProviderType(StrEnum):
    """Structured chat-model adapters available at the application boundary."""

    FAKE = "fake"
    OPENAI = "openai"


class Settings(BaseSettings):
    """Validated settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="IT_SUPPORT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Enterprise IT Support AI Agent"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr
    test_database_url: SecretStr | None = None
    knowledge_storage_path: Path = Path("data/knowledge")
    knowledge_max_file_size_bytes: int = Field(default=5_000_000, gt=0)
    knowledge_chunk_size: int = Field(default=500, ge=2)
    knowledge_chunk_overlap: int = Field(default=50, ge=0)
    embedding_provider: EmbeddingProviderType = EmbeddingProviderType.FAKE
    embedding_model: str = Field(default="fake-embedding-v1", min_length=1, max_length=200)
    embedding_dimension: int = Field(default=8, ge=1, le=2000)
    embedding_version: str = Field(default="v1", min_length=1, max_length=100)
    embedding_batch_size: int = Field(default=32, ge=1, le=2048)
    retrieval_embedding_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    embedding_api_key: SecretStr | None = None
    embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        min_length=1,
        max_length=500,
    )
    model_provider: ModelProviderType = ModelProviderType.FAKE
    model_name: str = Field(default="fake-chat-v1", min_length=1, max_length=200)
    model_api_key: SecretStr | None = None
    model_base_url: str = Field(
        default="https://api.openai.com/v1",
        min_length=1,
        max_length=500,
    )
    model_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    model_max_attempts: int = Field(default=2, ge=1, le=5)
    model_max_output_tokens: int = Field(default=1200, ge=1, le=16000)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_max_context_chars: int = Field(default=12000, ge=1000, le=100000)
    rag_min_keyword_score: float = Field(default=0.001, ge=0)
    rag_min_vector_similarity: float = Field(default=0.75, ge=-1, le=1)
    rag_vector_threshold_profile: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def require_isolated_test_database(self) -> "Settings":
        """Prevent test runs from silently using the development database."""
        if self.environment is Environment.TEST and self.test_database_url is None:
            raise ValueError("test environment requires a separate test database URL")
        if (
            self.environment is Environment.TEST
            and self.test_database_url is not None
            and self.test_database_url.get_secret_value() == self.database_url.get_secret_value()
        ):
            raise ValueError("test and development database URLs must differ")
        if self.knowledge_chunk_overlap >= self.knowledge_chunk_size:
            raise ValueError("knowledge chunk overlap must be smaller than chunk size")
        if self.environment is Environment.TEST and (
            self.embedding_provider is not EmbeddingProviderType.FAKE
        ):
            raise ValueError("test environment must use fake embedding provider")
        if self.embedding_provider is EmbeddingProviderType.OPENAI and (
            self.embedding_api_key is None or not self.embedding_api_key.get_secret_value().strip()
        ):
            raise ValueError("OpenAI embedding provider requires an API key")
        if (
            self.embedding_provider is EmbeddingProviderType.OPENAI
            and self.rag_vector_threshold_profile != self.embedding_profile_key
        ):
            raise ValueError(
                "OpenAI vector relevance threshold must be bound to the active embedding profile"
            )
        if (
            self.environment is Environment.TEST
            and self.model_provider is not ModelProviderType.FAKE
        ):
            raise ValueError("test environment must use fake model provider")
        if self.model_provider is ModelProviderType.OPENAI and (
            self.model_api_key is None or not self.model_api_key.get_secret_value().strip()
        ):
            raise ValueError("OpenAI model provider requires an API key")
        return self

    @property
    def active_database_url(self) -> str:
        """Return the database URL for the selected environment profile."""
        if self.environment is Environment.TEST:
            assert self.test_database_url is not None
            return self.test_database_url.get_secret_value()
        return self.database_url.get_secret_value()

    @property
    def embedding_profile_key(self) -> str:
        """Return the exact model, dimension, and version used to calibrate relevance."""
        return f"{self.embedding_model}:{self.embedding_dimension}:{self.embedding_version}"


@lru_cache
def get_settings() -> Settings:
    """Load and cache process-wide settings."""
    return Settings()
