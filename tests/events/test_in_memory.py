"""Tests for mellivor_kernel.events.in_memory."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.events import Event, EventDispatchError, InMemoryEventBus


@dataclasses.dataclass(frozen=True, slots=True)
class _Alpha(Event):
    value: int = 0


@dataclasses.dataclass(frozen=True, slots=True)
class _Beta(Event):
    value: int = 0


class _RecordingHandler:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.received: list[Event] = []
        self._raises = raises

    def handle(self, event: Event) -> None:
        if self._raises is not None:
            raise self._raises
        self.received.append(event)


def test_publish_with_no_subscribers_is_a_silent_noop() -> None:
    bus = InMemoryEventBus()

    bus.publish(_Alpha())  # must not raise


def test_subscribe_then_publish_delivers_to_the_handler() -> None:
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    bus.subscribe(_Alpha, handler)

    event = _Alpha(value=1)
    bus.publish(event)

    assert handler.received == [event]


def test_publish_only_delivers_to_handlers_of_the_exact_event_type() -> None:
    bus = InMemoryEventBus()
    alpha_handler = _RecordingHandler()
    beta_handler = _RecordingHandler()
    bus.subscribe(_Alpha, alpha_handler)
    bus.subscribe(_Beta, beta_handler)

    bus.publish(_Alpha(value=1))

    assert len(alpha_handler.received) == 1
    assert beta_handler.received == []


def test_multiple_handlers_per_event_all_receive_it() -> None:
    bus = InMemoryEventBus()
    first = _RecordingHandler()
    second = _RecordingHandler()
    bus.subscribe(_Alpha, first)
    bus.subscribe(_Alpha, second)

    event = _Alpha(value=1)
    bus.publish(event)

    assert first.received == [event]
    assert second.received == [event]


def test_handlers_are_notified_in_subscription_order() -> None:
    bus = InMemoryEventBus()
    order: list[str] = []

    class _Named:
        def __init__(self, name: str) -> None:
            self._name = name

        def handle(self, event: Event) -> None:
            order.append(self._name)

    bus.subscribe(_Alpha, _Named("first"))
    bus.subscribe(_Alpha, _Named("second"))
    bus.subscribe(_Alpha, _Named("third"))

    bus.publish(_Alpha())

    assert order == ["first", "second", "third"]


def test_a_failing_handler_does_not_block_the_remaining_handlers() -> None:
    bus = InMemoryEventBus()
    failing = _RecordingHandler(raises=RuntimeError("boom"))
    healthy = _RecordingHandler()
    bus.subscribe(_Alpha, failing)
    bus.subscribe(_Alpha, healthy)

    event = _Alpha(value=1)
    bus.publish(event)  # must not raise

    assert healthy.received == [event]


def test_unsubscribe_stops_further_delivery() -> None:
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    registration = bus.subscribe(_Alpha, handler)

    bus.unsubscribe(registration)
    bus.publish(_Alpha(value=1))

    assert handler.received == []


def test_unsubscribe_only_affects_the_targeted_handler() -> None:
    bus = InMemoryEventBus()
    first = _RecordingHandler()
    second = _RecordingHandler()
    first_registration = bus.subscribe(_Alpha, first)
    bus.subscribe(_Alpha, second)

    bus.unsubscribe(first_registration)
    event = _Alpha(value=1)
    bus.publish(event)

    assert first.received == []
    assert second.received == [event]


def test_unsubscribe_unknown_registration_raises() -> None:
    bus = InMemoryEventBus()
    handler = _RecordingHandler()
    registration = bus.subscribe(_Alpha, handler)
    bus.unsubscribe(registration)

    with pytest.raises(EventDispatchError):
        bus.unsubscribe(registration)


def test_unsubscribe_registration_from_a_different_bus_raises() -> None:
    bus = InMemoryEventBus()
    other_bus = InMemoryEventBus()
    registration = other_bus.subscribe(_Alpha, _RecordingHandler())

    with pytest.raises(EventDispatchError):
        bus.unsubscribe(registration)
