"""Tests for mellivor_kernel.events.handler."""

from __future__ import annotations

from mellivor_kernel.events import Event, EventHandler


class _Handler:
    def __init__(self) -> None:
        self.received: list[Event] = []

    def handle(self, event: Event) -> None:
        self.received.append(event)


def test_object_with_handle_method_satisfies_the_protocol() -> None:
    handler = _Handler()

    assert isinstance(handler, EventHandler)


def test_object_without_handle_method_does_not_satisfy_the_protocol() -> None:
    assert isinstance(object(), EventHandler) is False


def test_handler_receives_the_published_event() -> None:
    handler = _Handler()
    event = Event()

    handler.handle(event)

    assert handler.received == [event]
