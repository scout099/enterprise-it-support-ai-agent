"""Replaceable embedding providers used by knowledge indexing."""

from collections.abc import Sequence
from hashlib import sha256
from math import sqrt
from typing import Protocol

from openai import AsyncOpenAI


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider cannot return a usable response."""


class EmbeddingProvider(Protocol):
    """Public boundary for document and query embedding generation."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document texts in input order."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed one search query in the same vector space."""
        ...


class FakeEmbeddingProvider:
    """Generate deterministic, normalized vectors without external calls."""

    def __init__(self, *, dimension: int) -> None:
        if dimension < 1:
            raise ValueError("Embedding dimension must be positive")
        self._dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one stable vector for each input text."""
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        """Use the same deterministic algorithm for a query."""
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self._dimension:
            digest = sha256(f"{counter}:{text}".encode()).digest()
            for offset in range(0, len(digest), 4):
                integer = int.from_bytes(digest[offset : offset + 4], "big")
                values.append((integer / 0xFFFFFFFF) * 2 - 1)
                if len(values) == self._dimension:
                    break
            counter += 1

        magnitude = sqrt(sum(value * value for value in values))
        if magnitude == 0:
            return values
        return [value / magnitude for value in values]


class OpenAIEmbeddingProvider:
    """Generate embeddings through OpenAI or an OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimension: int,
        base_url: str,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._dimension = dimension

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Request a batch and preserve the provider's input indexes."""
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(
                input=list(texts),
                model=self._model,
                dimensions=self._dimension,
                encoding_format="float",
            )
        except Exception as exception:
            raise EmbeddingProviderError(
                f"Embedding provider request failed: {type(exception).__name__}"
            ) from exception

        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]

    async def embed_query(self, text: str) -> list[float]:
        """Embed a query using the configured model and dimension."""
        embeddings = await self.embed_documents([text])
        if not embeddings:
            raise EmbeddingProviderError("Embedding provider returned no query vector")
        return embeddings[0]
