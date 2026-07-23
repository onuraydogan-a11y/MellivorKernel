"""Tests for mellivor_kernel.events.registration."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.events import Event, EventRegistration


def test_registration_holds_event_type() -> None:
    registration = EventRegistration(event_type=Event)

    assert registration.event_type is Event
    assert registration.registration_id


def test_registration_ids_are_unique() -> None:
    first = EventRegistration(event_type=Event)
    second = EventRegistration(event_type=Event)

    assert first.registration_id != second.registration_id


def test_registration_is_immutable() -> None:
    registration = EventRegistration(event_type=Event)

    with pytest.raises(dataclasses.FrozenInstanceError):
        registration.registration_id = "other"  # type: ignore[misc]
