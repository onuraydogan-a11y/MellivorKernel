"""Tests for mellivor_kernel.memory.sqlite_store."""

from __future__ import annotations

from pathlib import Path

import pytest

from mellivor_kernel.memory import MemoryEntry, MemoryError, MemoryQuery, SQLiteMemoryStore

# --- Contract parity with InMemoryStore (mirrors test_in_memory.py) --------


def test_empty_store_get_returns_none(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")

    assert store.get("missing") is None


def test_empty_store_search_returns_empty_result(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")

    result = store.search(MemoryQuery())

    assert len(result) == 0
    assert list(result) == []


def test_empty_store_delete_returns_false(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")

    assert store.delete("missing") is False


def test_add_then_get(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    entry = MemoryEntry(id="a", content="hello")

    store.add(entry)

    assert store.get("a") == entry


def test_add_overwrites_an_existing_entry_with_the_same_id(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="first"))
    store.add(MemoryEntry(id="a", content="second"))

    retrieved = store.get("a")

    assert retrieved is not None
    assert retrieved.content == "second"


def test_delete_removes_an_existing_entry(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))

    deleted = store.delete("a")

    assert deleted is True
    assert store.get("a") is None


def test_delete_of_unknown_id_returns_false_and_does_not_raise(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))

    deleted = store.delete("missing")

    assert deleted is False
    assert store.get("a") is not None


def test_clear_removes_every_entry(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    store.clear()

    assert store.get("a") is None
    assert store.get("b") is None
    assert len(store.search(MemoryQuery())) == 0


def test_search_with_no_filters_matches_everything(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    result = store.search(MemoryQuery())

    assert {entry.id for entry in result} == {"a", "b"}


def test_search_by_id(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))
    store.add(MemoryEntry(id="b", content="world"))

    result = store.search(MemoryQuery(id="b"))

    assert [entry.id for entry in result] == ["b"]


def test_search_by_tag(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))
    store.add(MemoryEntry(id="b", content="world", tags=frozenset({"place"})))

    result = store.search(MemoryQuery(tag="greeting"))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_metadata(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello", metadata={"source": "user"}))
    store.add(MemoryEntry(id="b", content="world", metadata={"source": "system"}))

    result = store.search(MemoryQuery(metadata={"source": "user"}))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_metadata_requires_every_key_to_match(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello", metadata={"source": "user", "lang": "en"}))
    store.add(MemoryEntry(id="b", content="world", metadata={"source": "user", "lang": "fr"}))

    result = store.search(MemoryQuery(metadata={"source": "user", "lang": "en"}))

    assert [entry.id for entry in result] == ["a"]


def test_search_by_exact_text_substring(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="the capital of France is Paris"))
    store.add(MemoryEntry(id="b", content="the capital of Japan is Tokyo"))

    result = store.search(MemoryQuery(text="France"))

    assert [entry.id for entry in result] == ["a"]


def test_search_combines_filters_with_and_semantics(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))
    store.add(MemoryEntry(id="b", content="hello", tags=frozenset({"other"})))

    result = store.search(MemoryQuery(tag="greeting", text="hello"))

    assert [entry.id for entry in result] == ["a"]


def test_search_with_no_matches_returns_empty_result(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello"))

    result = store.search(MemoryQuery(tag="nonexistent"))

    assert len(result) == 0


# --- Persistence-specific behavior ------------------------------------------


def test_entries_survive_store_recreation(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"
    store = SQLiteMemoryStore(path)
    store.add(MemoryEntry(id="a", content="hello", tags=frozenset({"greeting"})))
    store.close()

    reopened = SQLiteMemoryStore(path)

    retrieved = reopened.get("a")
    assert retrieved is not None
    assert retrieved.content == "hello"
    assert retrieved.tags == frozenset({"greeting"})


def test_persisted_data_survives_multiple_reopenings(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"

    first = SQLiteMemoryStore(path)
    first.add(MemoryEntry(id="a", content="first"))
    first.close()

    second = SQLiteMemoryStore(path)
    second.add(MemoryEntry(id="b", content="second"))
    second.close()

    third = SQLiteMemoryStore(path)
    result = third.search(MemoryQuery())

    assert {entry.id for entry in result} == {"a", "b"}


def test_deletion_persists_across_reopening(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"
    first = SQLiteMemoryStore(path)
    first.add(MemoryEntry(id="a", content="hello"))
    first.delete("a")
    first.close()

    reopened = SQLiteMemoryStore(path)

    assert reopened.get("a") is None


def test_overwrite_preserves_original_insertion_position(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="first"))
    store.add(MemoryEntry(id="b", content="second"))
    store.add(MemoryEntry(id="a", content="updated"))

    result = store.search(MemoryQuery())

    assert [entry.id for entry in result] == ["a", "b"]
    assert result.entries[0].content == "updated"


def test_context_manager_closes_the_connection(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"

    with SQLiteMemoryStore(path) as store:
        store.add(MemoryEntry(id="a", content="hello"))

    reopened = SQLiteMemoryStore(path)
    assert reopened.get("a") is not None


# --- Serialization / corruption / failure behavior --------------------------


def test_metadata_round_trips_through_json(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="hello", metadata={"count": 3, "active": True}))

    retrieved = store.get("a")

    assert retrieved is not None
    assert retrieved.metadata == {"count": 3, "active": True}


def test_non_json_serializable_metadata_raises_memory_error(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    entry = MemoryEntry(id="a", content="hello", metadata={"bad": object()})

    with pytest.raises(MemoryError):
        store.add(entry)


def test_opening_a_corrupt_file_raises_memory_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite"
    path.write_bytes(b"not a sqlite database")

    with pytest.raises(MemoryError):
        SQLiteMemoryStore(path)


def test_opening_a_path_with_missing_parent_directory_raises_memory_error(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "memory.sqlite"

    with pytest.raises(MemoryError):
        SQLiteMemoryStore(path)


# --- Isolation ---------------------------------------------------------------


def test_stores_backed_by_different_files_are_isolated(tmp_path: Path) -> None:
    store_a = SQLiteMemoryStore(tmp_path / "a.sqlite")
    store_b = SQLiteMemoryStore(tmp_path / "b.sqlite")

    store_a.add(MemoryEntry(id="a", content="only in a"))

    assert store_a.get("a") is not None
    assert store_b.get("a") is None


# --- Deterministic behavior ---------------------------------------------------


def test_search_ordering_is_deterministic_across_repeated_calls(tmp_path: Path) -> None:
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite")
    store.add(MemoryEntry(id="a", content="one"))
    store.add(MemoryEntry(id="b", content="two"))
    store.add(MemoryEntry(id="c", content="three"))

    first = [entry.id for entry in store.search(MemoryQuery())]
    second = [entry.id for entry in store.search(MemoryQuery())]

    assert first == second == ["a", "b", "c"]
