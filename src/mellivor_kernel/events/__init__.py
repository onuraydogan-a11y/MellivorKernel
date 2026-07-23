"""Public API of the kernel's event bus subsystem.

An in-process publish/subscribe abstraction -- not a distributed messaging
system, not Kafka, not Redis, not NATS. ``EventBus`` is a structural
contract; ``InMemoryEventBus`` is its only concrete implementation today. A
future distributed implementation can replace it without any change to a
publisher such as :class:`~mellivor_kernel.execution.engine.ExecutionEngine`
or :class:`~mellivor_kernel.authorization.engine.AuthorizationEngine`, both
of which depend only on ``EventBus``, never on ``InMemoryEventBus``.
"""

from __future__ import annotations

from mellivor_kernel.events.bus import EventBus
from mellivor_kernel.events.event import Event
from mellivor_kernel.events.exceptions import EventDispatchError
from mellivor_kernel.events.handler import EventHandler
from mellivor_kernel.events.in_memory import InMemoryEventBus
from mellivor_kernel.events.registration import EventRegistration

__all__ = [
    "Event",
    "EventBus",
    "EventDispatchError",
    "EventHandler",
    "EventRegistration",
    "InMemoryEventBus",
]
