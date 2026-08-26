"""Tests for mellivor_kernel.memory.store."""

from __future__ import annotations

from pathlib import Path

from mellivor_kernel.memory import InMemoryStore, Memory, MemoryStore, SQLiteMemoryStore


def test_in_memory_store_satisfies_the_protocol() -> None:
    assert isinstance(InMemoryStore(), MemoryStore)


def test_memory_facade_satisfies_the_protocol() -> None:
    assert isinstance(Memory(), MemoryStore)


def test_sqlite_memory_store_satisfies_the_protocol(tmp_path: Path) -> None:
    assert isinstance(SQLiteMemoryStore(tmp_path / "memory.sqlite"), MemoryStore)
