"""Tests for mellivor_kernel.memory.memory."""

from __future__ import annotations

from mellivor_kernel.memory import InMemoryStore, Memory, MemoryEntry, MemoryQuery


def test_memory_defaults_to_an_in_memory_store() -> None:
    memory = Memory()
    memory.add(MemoryEntry(id="a", content="hello"))

    assert memory.get("a") is not None


def test_memory_delegates_to_the_given_store() -> None:
    store = InMemoryStore()
    memory = Memory(store)

    memory.add(MemoryEntry(id="a", content="hello"))

    assert store.get("a") is not None


def test_memory_add_get_search_delete_clear() -> None:
    memory = Memory()
    memory.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))

    assert memory.get("a") is not None
    assert len(memory.search(MemoryQuery(tag="greeting"))) == 1

    deleted = memory.delete("a")
    assert deleted is True
    assert memory.get("a") is None

    memory.add(MemoryEntry(id="b", content="world"))
    memory.clear()
    assert memory.get("b") is None
