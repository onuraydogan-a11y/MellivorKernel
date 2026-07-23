"""Structural contracts for the kernel's observability foundation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mellivor_kernel.observability.context import ObservationContext


@runtime_checkable
class MetricsRecorder(Protocol):
    """A structural contract for emitting numeric observations."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        context: ObservationContext | None = None,
    ) -> None:
        """Record a counter-style observation."""
        ...


@runtime_checkable
class TraceSpan(Protocol):
    """A minimal tracing span contract."""

    def end(self) -> None:
        """Complete the span."""
        ...


@runtime_checkable
class TraceRecorder(Protocol):
    """A structural contract for span creation and management."""

    def start_span(
        self,
        name: str,
        *,
        context: ObservationContext | None = None,
    ) -> TraceSpan:
        """Begin a trace span for an operation."""
        ...


@runtime_checkable
class StructuredEventSink(Protocol):
    """A structural contract for structured observation events."""

    def emit(self, event: Any) -> None:
        """Emit a structured observation event."""
        ...
