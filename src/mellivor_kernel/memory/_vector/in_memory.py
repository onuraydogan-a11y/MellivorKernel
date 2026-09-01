"""Dependency-free, non-production exact in-memory vector-store proof."""

from __future__ import annotations

import math
import re

from mellivor_kernel.memory._vector.contracts import (
    VectorMatch,
    VectorRecord,
    VectorStoreError,
    normalize_vector,
)

_NAMESPACE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class InMemoryVectorStore:
    """Exact, deterministic, process-local vector storage for contract proof.

    This implementation is nonpersistent, non-thread-safe, dependency-free,
    and not intended for production or scalable nearest-neighbor search.
    """

    def __init__(self, dimensions: int) -> None:
        if not isinstance(dimensions, int) or isinstance(dimensions, bool) or dimensions <= 0:
            raise VectorStoreError("Vector store dimensions must be a positive integer.")
        self._dimensions = dimensions
        self._namespaces: dict[str, dict[str, VectorRecord]] = {}

    @property
    def dimensions(self) -> int:
        """Return the fixed vector dimension for this store."""
        return self._dimensions

    def upsert(self, records: tuple[VectorRecord, ...], *, namespace: str) -> None:
        """Validate the whole batch, then insert or replace it."""
        _validate_namespace(namespace)
        if not isinstance(records, tuple) or not records:
            raise VectorStoreError("Vector upsert requires a non-empty record tuple.")

        validated: list[VectorRecord] = []
        identifiers: set[str] = set()
        for record in records:
            if not isinstance(record, VectorRecord):
                raise VectorStoreError("Vector upsert accepts only VectorRecord values.")
            if record.id in identifiers:
                raise VectorStoreError("Vector upsert batch contains a duplicate record ID.")
            if len(record.vector) != self._dimensions:
                raise VectorStoreError("Vector record has the wrong dimensions for this store.")
            identifiers.add(record.id)
            validated.append(record)

        target = self._namespaces.setdefault(namespace, {})
        target.update((record.id, record) for record in validated)

    def query(
        self, vector: tuple[float, ...], *, namespace: str, limit: int
    ) -> tuple[VectorMatch, ...]:
        """Return exact cosine results in descending-score/ID order."""
        _validate_namespace(namespace)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise VectorStoreError("Vector query limit must be a positive integer.")
        query_vector = normalize_vector(
            vector, dimensions=self._dimensions, field_name="query vector"
        )

        matches = [
            VectorMatch(
                id=record.id,
                score=_cosine_similarity(query_vector, record.vector),
                metadata=record.metadata,
            )
            for record in self._namespaces.get(namespace, {}).values()
        ]
        matches.sort(key=lambda match: (-match.score, match.id))
        return tuple(matches[:limit])

    def fetch(self, record_ids: tuple[str, ...], *, namespace: str) -> tuple[VectorRecord, ...]:
        """Return present records in requested-ID order."""
        _validate_namespace(namespace)
        identifiers = _validate_record_ids(record_ids)
        records = self._namespaces.get(namespace, {})
        return tuple(records[record_id] for record_id in identifiers if record_id in records)

    def delete(self, record_ids: tuple[str, ...], *, namespace: str) -> None:
        """Idempotently remove IDs from exactly one namespace."""
        _validate_namespace(namespace)
        identifiers = _validate_record_ids(record_ids)
        records = self._namespaces.get(namespace)
        if records is None:
            return
        for record_id in identifiers:
            records.pop(record_id, None)
        if not records:
            self._namespaces.pop(namespace, None)


def _validate_namespace(namespace: object) -> None:
    if not isinstance(namespace, str) or _NAMESPACE_PATTERN.fullmatch(namespace) is None:
        raise VectorStoreError("Vector namespace has an invalid format.")


def _validate_record_ids(record_ids: object) -> tuple[str, ...]:
    if not isinstance(record_ids, tuple):
        raise VectorStoreError("Vector record IDs must be a tuple.")
    seen: set[str] = set()
    for record_id in record_ids:
        if not isinstance(record_id, str) or not record_id.strip():
            raise VectorStoreError("Vector record IDs must be non-blank strings.")
        if record_id in seen:
            raise VectorStoreError("Vector record IDs must not contain duplicates.")
        seen.add(record_id)
    return record_ids


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_norm = math.hypot(*left)
    right_norm = math.hypot(*right)
    score = math.fsum(
        (left_value / left_norm) * (right_value / right_norm)
        for left_value, right_value in zip(left, right, strict=True)
    )
    return max(-1.0, min(1.0, score))
