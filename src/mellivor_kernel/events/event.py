"""Event: the immutable base type every kernel event derives from."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """The immutable base type every kernel event derives from.

    Carries only identity and timing -- concrete event types (for example
    :class:`~mellivor_kernel.execution.events.ExecutionStarted`) add their
    own fields describing what happened. Declared ``kw_only`` so subclasses
    can add required, non-default fields of their own without conflicting
    with this base class's defaulted fields.

    Attributes:
        event_id: A unique identifier for this event instance.
        occurred_at: When this event was constructed, in UTC.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
