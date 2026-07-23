"""MemoryEntry: an immutable record stored in memory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from mellivor_kernel.memory.exceptions import MemoryError


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """An immutable text memory record.

    Attributes:
        id: A caller-chosen, unique identifier for this entry.
            :meth:`~mellivor_kernel.memory.store.MemoryStore.add`-ing an
            entry whose ``id`` already exists overwrites the previous
            entry -- ``id`` is a stable key, not a correlation token.
        content: The text being remembered.
        tags: Free-form labels for coarse-grained filtering during
            search.
        metadata: Additional structured information about this entry.
        created_at: When this entry was constructed, in UTC.
    """

    id: str
    content: str
    tags: frozenset[str] = field(default_factory=frozenset)
    metadata: Mapping[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            MemoryError: If ``id`` or ``content`` is blank.
        """
        if not self.id.strip():
            raise MemoryError("MemoryEntry.id must not be blank.")
        if not self.content.strip():
            raise MemoryError("MemoryEntry.content must not be blank.")
