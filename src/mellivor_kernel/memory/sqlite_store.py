"""SQLiteMemoryStore: a durable, file-backed MemoryStore implementation."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from mellivor_kernel.memory.entry import MemoryEntry
from mellivor_kernel.memory.exceptions import MemoryError
from mellivor_kernel.memory.query import MemoryQuery
from mellivor_kernel.memory.result import MemoryResult

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_UPSERT = """
INSERT INTO memory_entries (id, content, tags, metadata, created_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    content = excluded.content,
    tags = excluded.tags,
    metadata = excluded.metadata,
    created_at = excluded.created_at
"""

_SELECT_ONE = "SELECT id, content, tags, metadata, created_at FROM memory_entries WHERE id = ?"

_SELECT_ALL = "SELECT id, content, tags, metadata, created_at FROM memory_entries ORDER BY rowid"

_DELETE_ONE = "DELETE FROM memory_entries WHERE id = ?"

_DELETE_ALL = "DELETE FROM memory_entries"


class SQLiteMemoryStore:
    """A durable :class:`~mellivor_kernel.memory.store.MemoryStore`,
    backed by a single SQLite database file.

    Unlike :class:`~mellivor_kernel.memory.in_memory.InMemoryStore`,
    entries survive process restart: the caller supplies a file path, and
    every entry is persisted to it. Uses only the Python standard library
    (``sqlite3``) -- no new dependency, mandatory or optional. See
    `ADR-0021 <../../docs/adr/0021-persistent-memory-sqlite-store.md>`_
    for the full design rationale.

    Backend-specific constraint beyond the ``MemoryStore`` contract:
    :attr:`~mellivor_kernel.memory.entry.MemoryEntry.tags` and
    :attr:`~mellivor_kernel.memory.entry.MemoryEntry.metadata` values must
    be JSON-serializable -- :meth:`add` raises
    :class:`~mellivor_kernel.memory.exceptions.MemoryError` if they are
    not. ``InMemoryStore`` has no such constraint.

    Not safe to share across threads without external synchronization --
    the same limitation ``InMemoryStore`` has as a plain, unlocked
    ``dict``. Safe for multiple processes to open the same file
    concurrently; SQLite's own file-level locking (WAL journal mode)
    governs that access.

    A ``SQLiteMemoryStore`` may be used as a context manager for
    deterministic cleanup of its file handle::

        with SQLiteMemoryStore(path) as store:
            store.add(entry)
    """

    def __init__(self, path: str | Path) -> None:
        """Open (creating if necessary) a SQLite-backed memory store.

        Args:
            path: The database file's location. No default is provided --
                storage ownership stays with the caller, per ADR-0004. The
                parent directory must already exist.

        Raises:
            MemoryError: If the file cannot be opened as a SQLite
                database (including an existing, corrupt, non-SQLite
                file at ``path``, or a missing parent directory).
        """
        self._path = Path(path)
        try:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=True)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            with self._conn:
                self._conn.execute(_CREATE_TABLE)
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to open SQLite memory store at {self._path}: {exc}") from exc

    def add(self, entry: MemoryEntry) -> None:
        """Store ``entry``, overwriting any existing entry with the same ``id``.

        Args:
            entry: The entry to store. Its ``tags`` and ``metadata`` must
                be JSON-serializable.

        Raises:
            MemoryError: If ``tags``/``metadata`` is not
                JSON-serializable, or the underlying store fails.
        """
        tags_json = json.dumps(sorted(entry.tags))
        try:
            metadata_json = json.dumps(dict(entry.metadata))
        except TypeError as exc:
            raise MemoryError(
                f"MemoryEntry.metadata for id={entry.id!r} is not JSON-serializable: {exc}"
            ) from exc
        try:
            with self._conn:
                self._conn.execute(
                    _UPSERT,
                    (
                        entry.id,
                        entry.content,
                        tags_json,
                        metadata_json,
                        entry.created_at.isoformat(),
                    ),
                )
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to store entry id={entry.id!r}: {exc}") from exc

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Look up a single entry by id.

        Args:
            entry_id: The id to look up.

        Returns:
            The matching entry, or ``None`` if no entry has that id.

        Raises:
            MemoryError: If the underlying store fails.
        """
        try:
            row = self._conn.execute(_SELECT_ONE, (entry_id,)).fetchone()
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to read entry id={entry_id!r}: {exc}") from exc
        return _row_to_entry(row) if row is not None else None

    def search(self, query: MemoryQuery) -> MemoryResult:
        """Find every entry matching ``query``.

        Args:
            query: The filters to match against.

        Returns:
            A :class:`~mellivor_kernel.memory.result.MemoryResult`
            wrapping every matching entry, ordered by insertion (an
            overwrite preserves the original position); empty if none
            match.

        Raises:
            MemoryError: If the underlying store fails.
        """
        try:
            rows = self._conn.execute(_SELECT_ALL).fetchall()
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to search memory store: {exc}") from exc
        entries = tuple(_row_to_entry(row) for row in rows)
        matches = tuple(entry for entry in entries if _matches(entry, query))
        return MemoryResult(entries=matches)

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by id.

        Args:
            entry_id: The id to remove.

        Returns:
            ``True`` if an entry with that id was removed, ``False`` if
            no entry had that id.

        Raises:
            MemoryError: If the underlying store fails.
        """
        try:
            with self._conn:
                cursor = self._conn.execute(_DELETE_ONE, (entry_id,))
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to delete entry id={entry_id!r}: {exc}") from exc
        return cursor.rowcount > 0

    def clear(self) -> None:
        """Remove every entry. The store remains open and usable.

        Raises:
            MemoryError: If the underlying store fails.
        """
        try:
            with self._conn:
                self._conn.execute(_DELETE_ALL)
        except sqlite3.Error as exc:
            raise MemoryError(f"Failed to clear memory store: {exc}") from exc

    def close(self) -> None:
        """Close the underlying SQLite connection.

        Not required before process exit; provided for callers that want
        deterministic release of the file handle.
        """
        self._conn.close()

    def __enter__(self) -> SQLiteMemoryStore:
        """Return ``self`` for use in a ``with`` block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the store on exit from a ``with`` block."""
        self.close()


def _row_to_entry(row: tuple[Any, ...]) -> MemoryEntry:
    """Reconstruct a :class:`MemoryEntry` from a raw database row."""
    entry_id, content, tags_json, metadata_json, created_at_iso = row
    return MemoryEntry(
        id=entry_id,
        content=content,
        tags=frozenset(json.loads(tags_json)),
        metadata=json.loads(metadata_json),
        created_at=datetime.fromisoformat(created_at_iso),
    )


def _matches(entry: MemoryEntry, query: MemoryQuery) -> bool:
    """Return whether ``entry`` satisfies every filter set on ``query``.

    Deliberately duplicates
    :mod:`~mellivor_kernel.memory.in_memory`'s private predicate rather
    than importing it, to avoid an undocumented coupling between the two
    backend modules; see ADR-0021's "Alternatives considered".
    """
    if query.id is not None and entry.id != query.id:
        return False
    if query.tag is not None and query.tag not in entry.tags:
        return False
    if query.text is not None and query.text not in entry.content:
        return False
    return all(entry.metadata.get(key) == value for key, value in query.metadata.items())
