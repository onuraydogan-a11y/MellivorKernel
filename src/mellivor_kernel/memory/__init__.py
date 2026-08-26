"""Public API of the kernel's memory subsystem.

Memory is kernel infrastructure, not an LLM feature: this package has no
dependency on any provider, workflow, or agent concept, and never will --
see ADR-0009. It supports plain text memory only: no embeddings, vector
database, semantic search, RAG, or agent-specific memory. ``MemoryStore``
is a structural contract with two concrete implementations today --
``InMemoryStore`` (ephemeral, no persistence) and ``SQLiteMemoryStore``
(durable, file-backed; see ADR-0021) -- either a drop-in replacement for
the other from a consumer's point of view, such as
:class:`~mellivor_kernel.execution.engine.ExecutionEngine`, which depends
only on ``MemoryStore``, never on a concrete backend.
"""

from __future__ import annotations

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.exceptions import MemoryError
from mellivor_kernel.memory.in_memory import InMemoryStore
from mellivor_kernel.memory.memory import Memory
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult
from mellivor_kernel.memory.sqlite_store import SQLiteMemoryStore
from mellivor_kernel.memory.store import MemoryStore

__all__ = [
    "InMemoryStore",
    "Memory",
    "MemoryEntry",
    "MemoryError",
    "MemoryQuery",
    "MemoryResult",
    "MemoryStore",
    "SQLiteMemoryStore",
]
