"""Experimental embedding contracts and proof adapter from ADR-0027.

This internal package is outside the stable v1.x compatibility promise. Its
types are deliberately not re-exported from :mod:`mellivor_kernel.providers`.
"""

from __future__ import annotations

from mellivor_kernel.providers._embeddings.contracts import (
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
)
from mellivor_kernel.providers._embeddings.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
)

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "EmbeddingRequest",
    "EmbeddingResult",
    "OpenAICompatibleEmbeddingProvider",
]
