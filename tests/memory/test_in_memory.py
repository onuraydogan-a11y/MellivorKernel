"""Tests for mellivor_kernel.memory.in_memory."""

from __future__ import annotations

from mellivor_kernel.memory import InMemoryStore, MemoryEntry, MemoryQuery


def test_empty_store_get_returns_none() -> None:
    store = InMemoryStore()

    assert store.get("missing") is None


def test_empty_store_search_returns_empty_result() -> None:
    store = InMemoryStore()

    result = store.search(MemoryQuery())

    assert len(result) == 0
    assert list(result) == []


def test_empty_store_delete_returns_false() -> None:
    store = InMemoryStore()

    assert store.delete("missing") is False


def test_add_then_get() -> None:
    store = InMemoryStore()
    entry = MemoryEntry(id="a", content="hello")

    store.add(entry)

    assert store.get("a") == entry


def test_add_overwrites_an_existing_entry_with_the_same_id() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="first"))
    store.add(MemoryEntry(id="a", content="second"))

    retrieved = store.get("a")

    assert retrieved is not None
    assert retrieved.content == "second"


def test_delete_removes_an_existing_entry() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))

    deleted = store.delete("a")

    assert deleted is True
    assert store.get("a") is None


def test_delete_of_unknown_id_returns_false_and_does_not_raise() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))

    deleted = store.delete("missing")

    assert deleted is False
    assert store.get("a") is not None


def test_clear_removes_every_entry() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    store.clear()

    assert store.get("a") is None
    assert store.get("b") is None
    assert len(store.search(MemoryQuery())) == 0


def test_search_with_no_filters_matches_everything() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    result = store.search(MemoryQuery())

    assert {entry.id for entry in result} == {"a", "b"}


def test_search_by_id() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    result = store.search(MemoryQuery(id="b"))

    assert [entry.id for entry in result] == ["b"]


def test_search_by_tag() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))
    store.add(MemoryEntry(id="b", content="world", tags=frozenset({"place"})))

    result = store.search(MemoryQuery(tag="greeting"))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_metadata() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello", metadata={"source": "user"}))
    store.add(MemoryEntry(id="b", content="world", metadata={"source": "system"}))

    result = store.search(MemoryQuery(metadata={"source": "user"}))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_metadata_requires_every_key_to_match() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello", metadata={"source": "user", "lang": "en"}))
    store.add(MemoryEntry(id="b", content="world", metadata={"source": "user", "lang": "fr"}))

    result = store.search(MemoryQuery(metadata={"source": "user", "lang": "en"}))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_exact_text_substring() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="the capital of France is Paris"))
    store.add(MemoryEntry(id="b", content="the capital of Japan is Tokyo"))

    result = store.search(MemoryQuery(text="France"))

    assert [entry.id for entry in result] == ["a"]


def test_search_combines_filters_with_and_semantics() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))
    store.add(MemoryEntry(id="b", content="hello", tags=frozenset({"other"})))

    result = store.search(MemoryQuery(tag="greeting", text="hello"))

    assert [entry.id for entry in result] == ["a"]


def test_search_with_no_matches_returns_empty_result() -> None:
    store = InMemoryStore()
    store.add(MemoryEntry(id="a", content="hello"))

    result = store.search(MemoryQuery(tag="nonexistent"))

    assert len(result) == 0
