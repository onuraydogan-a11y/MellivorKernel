"""MemoryQuery: an immutable query for searching memory entries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    """An immutable, deterministic query over memory entries.

    Every provided filter must match for an entry to be included in the
    result (AND semantics). A query with no filters at all matches every
    entry in the store. No embedding, vector, or semantic matching is
    performed -- ``text`` is a plain, case-sensitive substring check.

    Attributes:
        id: Only the entry with this exact ``id``.
        tag: Only entries whose ``tags`` contains this tag.
        metadata: Only entries whose ``metadata`` contains every given
            key/value pair.
        text: Only entries whose ``content`` contains this substring.
    """

    id: str | None = None
    tag: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    text: str | None = None
