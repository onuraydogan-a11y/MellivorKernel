"""Public API of the kernel's memory subsystem.

Memory is kernel infrastructure, not an LLM feature: this package has no
dependency on any provider, workflow, or agent concept, and never will --
see ADR-0009. It supports plain text memory only: no embeddings, vector
database, semantic search, RAG, or persistence. ``MemoryStore`` is a
structural contract; ``InMemoryStore`` is its only concrete implementation
today, and a future persistent or vector-backed implementation can replace
it without any change to a consumer such as
:class:`~mellivor_kernel.execution.engine.ExecutionEngine`, which depends
only on ``MemoryStore``, never on ``InMemoryStore``.
"""

from __future__ import annotations

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.exceptions import MemoryError
from mellivor_kernel.memory.in_memory import InMemoryStore
from mellivor_kernel.memory.memory import Memory
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult
from mellivor_kernel.memory.store import MemoryStore

__all__ = [
    "InMemoryStore",
    "Memory",
    "MemoryEntry",
    "MemoryError",
    "MemoryQuery",
    "MemoryResult",
    "MemoryStore",
]
