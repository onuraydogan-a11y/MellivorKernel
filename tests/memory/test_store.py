"""Tests for mellivor_kernel.memory.store."""

from __future__ import annotations

from mellivor_kernel.memory import InMemoryStore, Memory, MemoryStore


def test_in_memory_store_satisfies_the_protocol() -> None:
    assert isinstance(InMemoryStore(), MemoryStore)


def test_memory_facade_satisfies_the_protocol() -> None:
    assert isinstance(Memory(), MemoryStore)
