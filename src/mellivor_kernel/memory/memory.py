"""Memory: the kernel's stable memory facade."""

from __future__ import annotations

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.in_memory import InMemoryStore
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult
from mellivor_kernel.memory.store import MemoryStore


class Memory:
    """The kernel's memory facade: a stable entry point over a pluggable
    :class:`~mellivor_kernel.memory.store.MemoryStore` backend.

    Memory is kernel infrastructure, not an LLM feature -- this class has
    no dependency on any provider, workflow, or agent concept, and never
    will: the dependency runs the other way (a provider may one day
    *consume* memory; memory never consumes a provider). Structurally
    satisfies ``MemoryStore`` itself, so a ``Memory`` instance can be
    handed anywhere a ``MemoryStore`` is expected -- for example
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`'s optional
    ``memory`` parameter.
    """

    def __init__(self, store: MemoryStore | None = None) -> None:
        """Initialize the facade.

        Args:
            store: The backend to delegate to. A new
                :class:`~mellivor_kernel.memory.in_memory.InMemoryStore`
                is created if one is not provided.
        """
        self._store = store if store is not None else InMemoryStore()

    def add(self, entry: MemoryEntry) -> None:
        """Store ``entry``, overwriting any existing entry with the same ``id``.

        Args:
            entry: The entry to store.
        """
        self._store.add(entry)

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Look up a single entry by id.

        Args:
            entry_id: The id to look up.

        Returns:
            The matching entry, or ``None`` if no entry has that id.
        """
        return self._store.get(entry_id)

    def search(self, query: MemoryQuery) -> MemoryResult:
        """Find every entry matching ``query``.

        Args:
            query: The filters to match against.

        Returns:
            A :class:`MemoryResult` wrapping every matching entry; empty
            if none match.
        """
        return self._store.search(query)

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by id.

        Args:
            entry_id: The id to remove.

        Returns:
            ``True`` if an entry with that id was removed, ``False`` if
            no entry had that id.
        """
        return self._store.delete(entry_id)

    def clear(self) -> None:
        """Remove every entry."""
        self._store.clear()
