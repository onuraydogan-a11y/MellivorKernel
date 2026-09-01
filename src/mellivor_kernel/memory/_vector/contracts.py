"""Internal vector-store contract values defined by ADR-0027."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from mellivor_kernel.memory.exceptions import MemoryError

type MetadataValue = str | int | float | bool | None
type VectorMetadata = Mapping[str, MetadataValue]


class VectorStoreError(MemoryError):
    """Translated failure at the experimental vector-store boundary."""


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """A caller-identified vector with portable scalar metadata."""

    id: str
    vector: tuple[float, ...] = field(repr=False)
    metadata: VectorMetadata = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise VectorStoreError("VectorRecord.id must be a non-blank string.")
        object.__setattr__(
            self, "vector", normalize_vector(self.vector, field_name="record vector")
        )
        object.__setattr__(self, "metadata", snapshot_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """A deterministic cosine match without the stored vector payload."""

    id: str
    score: float
    metadata: VectorMetadata = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise VectorStoreError("VectorMatch.id must be a non-blank string.")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise VectorStoreError("VectorMatch.score must be a real number.")
        score = float(self.score)
        if not math.isfinite(score) or not -1.0 <= score <= 1.0:
            raise VectorStoreError("VectorMatch.score must be finite and between -1 and 1.")
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "metadata", snapshot_metadata(self.metadata))


@runtime_checkable
class VectorStore(Protocol):
    """Structural contract for experimental cosine vector stores."""

    @property
    def dimensions(self) -> int:
        """Return the fixed positive vector dimension for this store."""
        ...

    def upsert(self, records: tuple[VectorRecord, ...], *, namespace: str) -> None:
        """Insert or replace one validated non-empty record batch."""
        ...

    def query(
        self, vector: tuple[float, ...], *, namespace: str, limit: int
    ) -> tuple[VectorMatch, ...]:
        """Return exact cosine matches in deterministic order."""
        ...

    def fetch(self, record_ids: tuple[str, ...], *, namespace: str) -> tuple[VectorRecord, ...]:
        """Fetch present records in requested-ID order, omitting misses."""
        ...

    def delete(self, record_ids: tuple[str, ...], *, namespace: str) -> None:
        """Idempotently delete IDs from one namespace."""
        ...


def normalize_vector(
    vector: object,
    *,
    dimensions: int | None = None,
    field_name: str = "vector",
) -> tuple[float, ...]:
    """Validate and normalize one finite, non-zero vector."""
    if not isinstance(vector, (list, tuple)) or not vector:
        raise VectorStoreError(f"{field_name.capitalize()} must be a non-empty numeric sequence.")

    normalized: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VectorStoreError(f"{field_name.capitalize()} must contain only real numbers.")
        converted = float(value)
        if not math.isfinite(converted):
            raise VectorStoreError(f"{field_name.capitalize()} must contain only finite values.")
        normalized.append(converted)

    if dimensions is not None and len(normalized) != dimensions:
        raise VectorStoreError(f"{field_name.capitalize()} has the wrong dimensions.")
    if math.hypot(*normalized) == 0.0:
        raise VectorStoreError(f"{field_name.capitalize()} must have non-zero magnitude.")
    return tuple(normalized)


def snapshot_metadata(metadata: object) -> VectorMetadata:
    """Return a defensive read-only scalar-JSON metadata snapshot."""
    if not isinstance(metadata, Mapping):
        raise VectorStoreError("Vector metadata must be a mapping.")

    snapshot: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key.strip():
            raise VectorStoreError("Vector metadata keys must be non-blank strings.")
        if value is None or isinstance(value, (str, bool, int)):
            snapshot[key] = value
            continue
        if isinstance(value, float) and math.isfinite(value):
            snapshot[key] = value
            continue
        raise VectorStoreError("Vector metadata values must be finite JSON scalars.")
    return MappingProxyType(snapshot)
