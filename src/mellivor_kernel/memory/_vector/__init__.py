"""Experimental vector contracts and in-memory proof from ADR-0027.

This internal package is outside the stable v1.x compatibility promise. Its
types are deliberately not re-exported from :mod:`mellivor_kernel.memory`.
"""

from __future__ import annotations

from mellivor_kernel.memory._vector.contracts import (
    VectorMatch,
    VectorRecord,
    VectorStore,
    VectorStoreError,
)
from mellivor_kernel.memory._vector.in_memory import InMemoryVectorStore

__all__ = [
    "InMemoryVectorStore",
    "VectorMatch",
    "VectorRecord",
    "VectorStore",
    "VectorStoreError",
]
