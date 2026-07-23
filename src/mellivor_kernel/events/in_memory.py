"""InMemoryEventBus: an in-process EventBus implementation."""

from __future__ import annotations

from mellivor_kernel.core.logging import get_logger
from mellivor_kernel.events.event import Event
from mellivor_kernel.events.exceptions import EventDispatchError
from mellivor_kernel.events.handler import EventHandler
from mellivor_kernel.events.registration import EventRegistration


class InMemoryEventBus:
    """An in-process :class:`~mellivor_kernel.events.bus.EventBus`: publishes
    synchronously to in-memory handlers, keyed by each event's exact type
    (no subscription to a base class receives subtype events).

    This is not a distributed messaging system -- there is no persistence,
    no cross-process delivery, and no ordering guarantee beyond a single
    process. It exists so ``EventBus`` has one concrete, dependency-free
    implementation today; a future Kafka/NATS/Redis-backed implementation
    is a drop-in replacement for this class, never a change to
    ``ExecutionEngine``/``AuthorizationEngine``.
    """

    def __init__(self) -> None:
        """Initialize an empty bus."""
        self._handlers: dict[type[Event], dict[str, EventHandler]] = {}
        self._logger = get_logger("events")

    def publish(self, event: Event) -> None:
        """Publish ``event`` to every handler subscribed to its exact type.

        Handlers are notified in subscription order. A handler's own
        exception is caught and logged, never propagated -- one failing
        handler must never block delivery to the remaining handlers, or to
        the caller that published the event.

        Args:
            event: The event to publish.
        """
        for handler in list(self._handlers.get(type(event), {}).values()):
            try:
                handler.handle(event)
            except Exception as exc:
                self._logger.warning(
                    "Event handler %r raised while handling %r: %s",
                    handler,
                    type(event).__name__,
                    exc,
                )

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration:
        """Subscribe ``handler`` to every future event of exactly ``event_type``.

        Multiple handlers may subscribe to the same ``event_type``; they
        are notified in subscription order.

        Args:
            event_type: The event type to subscribe to.
            handler: The handler to notify.

        Returns:
            A registration handle; pass it to :meth:`unsubscribe` to stop
            receiving events.
        """
        registration = EventRegistration(event_type=event_type)
        self._handlers.setdefault(event_type, {})[registration.registration_id] = handler
        return registration

    def unsubscribe(self, registration: EventRegistration) -> None:
        """Remove a previously created subscription.

        Args:
            registration: The registration returned by :meth:`subscribe`.

        Raises:
            EventDispatchError: If ``registration`` is not an active
                subscription on this bus (already unsubscribed, or issued
                by a different bus instance).
        """
        handlers = self._handlers.get(registration.event_type)
        if handlers is None or registration.registration_id not in handlers:
            raise EventDispatchError(f"{registration!r} is not an active subscription.")
        del handlers[registration.registration_id]
