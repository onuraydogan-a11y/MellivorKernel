"""InMemoryStore: an in-process MemoryStore implementation."""

from __future__ import annotations

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult


class InMemoryStore:
    """An in-process :class:`~mellivor_kernel.memory.store.MemoryStore`:
    plain text memory held in a dict, keyed by
    :attr:`~mellivor_kernel.memory.entry.MemoryEntry.id`.

    No persistence, no embeddings, no vector search -- entries do not
    survive process restart, and :meth:`search` performs only exact/
    substring matching. This exists so ``MemoryStore`` has one concrete,
    dependency-free implementation today; a future persistent or vector-
    backed store is a drop-in replacement for this class, never a change
    to a consumer such as
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`.
    """

    def __init__(self) -> None:
        """Initialize an empty store."""
        self._entries: dict[str, MemoryEntry] = {}

    def add(self, entry: MemoryEntry) -> None:
        """Store ``entry``, overwriting any existing entry with the same ``id``.

        Args:
            entry: The entry to store.
        """
        self._entries[entry.id] = entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Look up a single entry by id.

        Args:
            entry_id: The id to look up.

        Returns:
            The matching entry, or ``None`` if no entry has that id.
        """
        return self._entries.get(entry_id)

    def search(self, query: MemoryQuery) -> MemoryResult:
        """Find every entry matching ``query``.

        Every filter set on ``query`` must match (AND semantics); a query
        with no filters at all matches every entry, in insertion order.

        Args:
            query: The filters to match against.

        Returns:
            A :class:`MemoryResult` wrapping every matching entry; empty
            if none match.
        """
        matches = tuple(entry for entry in self._entries.values() if _matches(entry, query))
        return MemoryResult(entries=matches)

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by id.

        Args:
            entry_id: The id to remove.

        Returns:
            ``True`` if an entry with that id was removed, ``False`` if
            no entry had that id.
        """
        return self._entries.pop(entry_id, None) is not None

    def clear(self) -> None:
        """Remove every entry."""
        self._entries.clear()


def _matches(entry: MemoryEntry, query: MemoryQuery) -> bool:
    """Return whether ``entry`` satisfies every filter set on ``query``."""
    if query.id is not None and entry.id != query.id:
        return False
    if query.tag is not None and query.tag not in entry.tags:
        return False
    if query.text is not None and query.text not in entry.content:
        return False
    return all(entry.metadata.get(key) == value for key, value in query.metadata.items())
