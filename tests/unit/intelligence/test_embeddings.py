"""Embedding provider contract tests."""

import pytest

from enterprise_it_support.intelligence.embeddings import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_fake_embedding_provider_is_stable_across_calls_and_instances() -> None:
    first_provider = FakeEmbeddingProvider(dimension=8)
    second_provider = FakeEmbeddingProvider(dimension=8)

    first_batch = await first_provider.embed_documents(["VPN timeout", "Outlook mailbox"])
    repeated_batch = await first_provider.embed_documents(["VPN timeout", "Outlook mailbox"])
    another_instance_batch = await second_provider.embed_documents(
        ["VPN timeout", "Outlook mailbox"]
    )
    query = await first_provider.embed_query("VPN timeout")

    assert first_batch == repeated_batch == another_instance_batch
    assert query == first_batch[0]
    assert first_batch[0] != first_batch[1]
    assert all(len(vector) == 8 for vector in first_batch)
