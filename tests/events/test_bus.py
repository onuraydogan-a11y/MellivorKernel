"""Tests for mellivor_kernel.events.bus."""

from __future__ import annotations

from mellivor_kernel.events import EventBus, InMemoryEventBus


def test_in_memory_event_bus_satisfies_the_event_bus_protocol() -> None:
    assert isinstance(InMemoryEventBus(), EventBus)
