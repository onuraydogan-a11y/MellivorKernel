"""Tests for mellivor_kernel.memory.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.memory import MemoryEntry, MemoryResult


def test_empty_result_defaults() -> None:
    result = MemoryResult()

    assert result.entries == ()
    assert len(result) == 0
    assert list(result) == []


def test_result_holds_and_iterates_entries() -> None:
    entry_a = MemoryEntry(id="a", content="hello")
    entry_b = MemoryEntry(id="b", content="world")

    result = MemoryResult(entries=(entry_a, entry_b))

    assert len(result) == 2
    assert list(result) == [entry_a, entry_b]


def test_result_is_immutable() -> None:
    result = MemoryResult()

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.entries = ()  # type: ignore[misc]
