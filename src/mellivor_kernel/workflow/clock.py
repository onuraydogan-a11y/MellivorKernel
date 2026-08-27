"""Clock: an injectable time source for scheduling-guard checks.

Exists so `WorkflowStep.not_before` (see ADR-0024) can be evaluated
deterministically in tests, with no real sleep or wall-clock dependency
-- never to support a background timer, poller, or scheduler. There is
no default global clock instance; `WorkflowEngine` constructs its own
`SystemClock()` at object-construction time if none is injected, never
at import time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """A source of the current time, injectable for deterministic tests."""

    def now(self) -> datetime:
        """Return the current time, as a timezone-aware ``datetime``."""
        ...


class SystemClock:
    """The real wall clock -- ``WorkflowEngine``'s default when no
    :class:`Clock` is injected.
    """

    def now(self) -> datetime:
        """Return the current time in UTC."""
        return datetime.now(UTC)
