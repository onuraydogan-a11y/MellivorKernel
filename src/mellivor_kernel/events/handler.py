"""EventHandler: the contract every event subscriber must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mellivor_kernel.events.event import Event


@runtime_checkable
class EventHandler(Protocol):
    """Anything capable of reacting to a published event."""

    def handle(self, event: Event) -> None:
        """Handle a published event.

        Args:
            event: The event that was published.
        """
        ...
