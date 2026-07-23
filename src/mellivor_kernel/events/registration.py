"""EventRegistration: an opaque handle to an active subscription."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mellivor_kernel.events.event import Event


@dataclass(frozen=True, slots=True)
class EventRegistration:
    """An opaque handle to an active subscription.

    Returned by :meth:`~mellivor_kernel.events.bus.EventBus.subscribe` and
    required by :meth:`~mellivor_kernel.events.bus.EventBus.unsubscribe`.
    Carries no reference to the handler itself -- a bus implementation is
    free to look it up however it stores subscriptions internally.

    Attributes:
        event_type: The event type this registration is subscribed to.
        registration_id: A unique identifier for this subscription.
    """

    event_type: type[Event]
    registration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
