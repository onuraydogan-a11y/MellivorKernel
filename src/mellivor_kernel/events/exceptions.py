"""Event bus exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class EventDispatchError(KernelError):
    """Raised when an event bus operation cannot be completed.

    Not raised for a handler's own exception during
    :meth:`~mellivor_kernel.events.bus.EventBus.publish` -- see
    :class:`~mellivor_kernel.events.in_memory.InMemoryEventBus`. Raised
    only for misuse of the bus API itself, such as unsubscribing a
    registration that is not (or is no longer) active.
    """
