"""EventBus: the structural contract every event bus implementation satisfies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mellivor_kernel.events.event import Event
from mellivor_kernel.events.handler import EventHandler
from mellivor_kernel.events.registration import EventRegistration


@runtime_checkable
class EventBus(Protocol):
    """The contract every event bus implementation satisfies.

    Publishers -- :class:`~mellivor_kernel.execution.engine.ExecutionEngine`,
    :class:`~mellivor_kernel.authorization.engine.AuthorizationEngine` --
    depend on this Protocol, never on a concrete implementation.
    :class:`~mellivor_kernel.events.in_memory.InMemoryEventBus` is the only
    implementation today; a future distributed implementation (Kafka, NATS,
    Redis) satisfies this same contract as a drop-in replacement, with no
    change required to either publisher.
    """

    def publish(self, event: Event) -> None:
        """Publish ``event`` to every handler subscribed to its exact type.

        Args:
            event: The event to publish.
        """
        ...

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration:
        """Subscribe ``handler`` to every future event of exactly ``event_type``.

        Args:
            event_type: The event type to subscribe to.
            handler: The handler to notify.

        Returns:
            A registration handle; pass it to :meth:`unsubscribe` to stop
            receiving events.
        """
        ...

    def unsubscribe(self, registration: EventRegistration) -> None:
        """Remove a previously created subscription.

        Args:
            registration: The registration returned by :meth:`subscribe`.
        """
        ...
