"""Tests for mellivor_kernel.memory.query."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.memory import MemoryQuery


def test_query_defaults_match_everything() -> None:
    query = MemoryQuery()

    assert query.id is None
    assert query.tag is None
    assert dict(query.metadata) == {}
    assert query.text is None


def test_query_accepts_all_filters() -> None:
    query = MemoryQuery(id="a", tag="greeting", metadata={"source": "test"}, text="hello")

    assert query.id == "a"
    assert query.tag == "greeting"
    assert query.metadata == {"source": "test"}
    assert query.text == "hello"


def test_query_is_immutable() -> None:
    query = MemoryQuery()

    with pytest.raises(dataclasses.FrozenInstanceError):
        query.tag = "other"  # type: ignore[misc]
