"""MemoryResult: the outcome of a memory search."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from mellivor_kernel.memory.entry import MemoryEntry


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """The immutable outcome of a
    :meth:`~mellivor_kernel.memory.store.MemoryStore.search`.

    Attributes:
        entries: The matching entries, in the backing store's own order.
            Empty (not an error) when nothing matches.
    """

    entries: tuple[MemoryEntry, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        """The number of matching entries."""
        return len(self.entries)

    def __iter__(self) -> Iterator[MemoryEntry]:
        """Iterate over the matching entries."""
        return iter(self.entries)
