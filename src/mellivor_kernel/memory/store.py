"""MemoryStore: the structural contract every memory backend satisfies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult


@runtime_checkable
class MemoryStore(Protocol):
    """The contract every memory backend satisfies.

    Consumers -- :class:`~mellivor_kernel.execution.engine.ExecutionEngine`,
    :class:`~mellivor_kernel.memory.memory.Memory` -- depend on this
    Protocol, never on a concrete backend. :class:`InMemoryStore` is the
    only implementation today; a future persistent or vector-backed store
    satisfies this same contract as a drop-in replacement, with no change
    required to any consumer.
    """

    def add(self, entry: MemoryEntry) -> None:
        """Store ``entry``, overwriting any existing entry with the same ``id``.

        Args:
            entry: The entry to store.
        """
        ...

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Look up a single entry by id.

        Args:
            entry_id: The id to look up.

        Returns:
            The matching entry, or ``None`` if no entry has that id.
        """
        ...

    def search(self, query: MemoryQuery) -> MemoryResult:
        """Find every entry matching ``query``.

        Args:
            query: The filters to match against.

        Returns:
            A :class:`MemoryResult` wrapping every matching entry; empty
            if none match.
        """
        ...

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by id.

        Args:
            entry_id: The id to remove.

        Returns:
            ``True`` if an entry with that id was removed, ``False`` if
            no entry had that id.
        """
        ...

    def clear(self) -> None:
        """Remove every entry."""
        ...
