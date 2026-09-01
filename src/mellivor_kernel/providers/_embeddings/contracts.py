"""Internal embedding contract values defined by ADR-0027."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from mellivor_kernel.providers.exceptions import ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck


class EmbeddingError(ProviderError):
    """Translated failure at the experimental embedding boundary."""


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """An ordered, non-empty batch of non-blank texts.

    Text values are excluded from the generated representation so ordinary
    diagnostics cannot disclose embedding inputs.
    """

    texts: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.texts, tuple) or not self.texts:
            raise EmbeddingError("EmbeddingRequest.texts must be a non-empty tuple.")
        if any(not isinstance(text, str) or not text.strip() for text in self.texts):
            raise EmbeddingError("Every embedding input must be a non-blank string.")


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Ordered embedding vectors plus actual model and dimension identity."""

    vectors: tuple[tuple[float, ...], ...] = field(repr=False)
    model: str
    dimensions: int

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise EmbeddingError("EmbeddingResult.model must be a non-blank string.")
        if (
            not isinstance(self.dimensions, int)
            or isinstance(self.dimensions, bool)
            or self.dimensions <= 0
        ):
            raise EmbeddingError("EmbeddingResult.dimensions must be a positive integer.")
        if not isinstance(self.vectors, tuple) or not self.vectors:
            raise EmbeddingError("EmbeddingResult.vectors must be a non-empty tuple.")

        normalized: list[tuple[float, ...]] = []
        for vector in self.vectors:
            normalized.append(
                _normalize_vector(vector, dimensions=self.dimensions, field_name="result vector")
            )
        object.__setattr__(self, "vectors", tuple(normalized))


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Synchronous structural contract for experimental embedding providers."""

    @property
    def name(self) -> str:
        """Return a stable non-blank provider identifier."""
        ...

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed one ordered batch or raise :class:`EmbeddingError`."""
        ...

    def check_health(self) -> ProviderHealthCheck:
        """Return an explicit point-in-time health report without raising."""
        ...


def normalize_vector(
    vector: object,
    *,
    dimensions: int | None = None,
    field_name: str = "vector",
) -> tuple[float, ...]:
    """Normalize a tuple/list of finite real numbers for an internal adapter."""
    return _normalize_vector(vector, dimensions=dimensions, field_name=field_name)


def _normalize_vector(
    vector: object,
    *,
    dimensions: int | None,
    field_name: str,
) -> tuple[float, ...]:
    if not isinstance(vector, (list, tuple)) or not vector:
        raise EmbeddingError(f"Embedding {field_name} must be a non-empty numeric sequence.")

    normalized: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EmbeddingError(f"Embedding {field_name} must contain only real numbers.")
        converted = float(value)
        if not math.isfinite(converted):
            raise EmbeddingError(f"Embedding {field_name} must contain only finite values.")
        normalized.append(converted)

    if dimensions is not None and len(normalized) != dimensions:
        raise EmbeddingError(
            f"Embedding {field_name} must contain exactly {dimensions} dimensions."
        )
    return tuple(normalized)
