"""No-op implementations for the kernel's observability foundation."""

from __future__ import annotations

from mellivor_kernel.observability.context import ObservationContext


class NoOpTraceSpan:
    """A no-op tracing span used when no trace backend is configured."""

    def end(self) -> None:
        """Discard the span end event."""


class NoOpMetricsRecorder:
    """A no-op metric recorder used by dependency-injected consumers."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        context: ObservationContext | None = None,
    ) -> None:
        """Silently discard metric observations."""


class NoOpTraceRecorder:
    """A no-op tracing recorder used when tracing is not configured."""

    def start_span(
        self,
        name: str,
        *,
        context: ObservationContext | None = None,
    ) -> NoOpTraceSpan:
        """Create a span that does nothing."""
        return NoOpTraceSpan()


class NoOpStructuredEventSink:
    """A no-op structured event sink used by default observability wiring."""

    def emit(self, event: object) -> None:
        """Silently discard structured events."""
