"""Tests for mellivor_kernel.events.event."""

from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from mellivor_kernel.events import Event


def test_event_auto_generates_id_and_timestamp() -> None:
    event = Event()

    assert isinstance(event.event_id, str) and event.event_id
    assert isinstance(event.occurred_at, datetime)


def test_event_ids_are_unique() -> None:
    assert Event().event_id != Event().event_id


def test_event_is_immutable() -> None:
    event = Event()

    with pytest.raises(dataclasses.FrozenInstanceError):
        event.event_id = "other"  # type: ignore[misc]


def test_subclass_can_add_required_fields() -> None:
    @dataclasses.dataclass(frozen=True, slots=True)
    class _Sub(Event):
        payload: str

    sub = _Sub(payload="hello")

    assert sub.payload == "hello"
    assert sub.event_id
    assert isinstance(sub.occurred_at, datetime)
