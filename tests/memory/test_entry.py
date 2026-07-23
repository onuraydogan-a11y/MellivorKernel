"""Tests for mellivor_kernel.memory.entry."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from mellivor_kernel.memory import MemoryEntry, MemoryError


def test_entry_defaults() -> None:
    entry = MemoryEntry(id="a", content="hello")

    assert entry.id == "a"
    assert entry.content == "hello"
    assert entry.tags == frozenset()
    assert dict(entry.metadata) == {}
    assert isinstance(entry.created_at, datetime)


def test_entry_accepts_tags_and_metadata() -> None:
    entry = MemoryEntry(
        id="a", content="hello", tags=frozenset({"greeting"}), metadata={"source": "test"}
    )

    assert entry.tags == frozenset({"greeting"})
    assert entry.metadata == {"source": "test"}


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_id_rejected(blank: str) -> None:
    with pytest.raises(MemoryError):
        MemoryEntry(id=blank, content="hello")


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_content_rejected(blank: str) -> None:
    with pytest.raises(MemoryError):
        MemoryEntry(id="a", content=blank)


def test_entry_is_immutable() -> None:
    entry = MemoryEntry(id="a", content="hello")

    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.content = "other"  # type: ignore[misc]
