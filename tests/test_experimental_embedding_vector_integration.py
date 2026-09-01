"""Synthetic experimental embedding-to-vector-store contract proof."""

from __future__ import annotations

import httpx

from mellivor_kernel.memory._vector import InMemoryVectorStore, VectorRecord
from mellivor_kernel.providers import ProviderConfiguration
from mellivor_kernel.providers._embeddings import (
    EmbeddingRequest,
    OpenAICompatibleEmbeddingProvider,
)


def test_embedding_upsert_and_query_are_deterministic() -> None:
    vectors = {
        "alpha document": [1.0, 0.0],
        "beta document": [0.0, 1.0],
        "alpha query": [0.9, 0.1],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        inputs = payload["input"]
        return httpx.Response(
            200,
            json={
                "model": "synthetic-embedding",
                "data": [
                    {"index": index, "embedding": vectors[text]}
                    for index, text in reversed(list(enumerate(inputs)))
                ],
            },
        )

    provider = OpenAICompatibleEmbeddingProvider(
        ProviderConfiguration(
            provider_name="openai-compatible-embedding",
            default_model="synthetic-embedding",
            base_url="http://synthetic.internal/v1",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    document_result = provider.embed(EmbeddingRequest(texts=("alpha document", "beta document")))
    store = InMemoryVectorStore(document_result.dimensions)
    store.upsert(
        tuple(
            VectorRecord(
                id=record_id,
                vector=vector,
                metadata={"kind": "synthetic"},
            )
            for record_id, vector in zip(("alpha", "beta"), document_result.vectors, strict=True)
        ),
        namespace="integration",
    )
    query_result = provider.embed(EmbeddingRequest(texts=("alpha query",)))

    matches = store.query(query_result.vectors[0], namespace="integration", limit=2)

    assert [match.id for match in matches] == ["alpha", "beta"]
    assert matches[0].score > matches[1].score
    assert matches[0].metadata == {"kind": "synthetic"}
