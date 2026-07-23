"""Public API of the kernel's observability foundation subsystem."""

from __future__ import annotations

from mellivor_kernel.observability.context import ObservationContext
from mellivor_kernel.observability.contracts import (
    MetricsRecorder,
    StructuredEventSink,
    TraceRecorder,
    TraceSpan,
)
from mellivor_kernel.observability.events import StructuredObservationEvent
from mellivor_kernel.observability.noops import (
    NoOpMetricsRecorder,
    NoOpStructuredEventSink,
    NoOpTraceRecorder,
)


class Observability:
    """Dependency-injected observability composition for kernel consumers."""

    def __init__(
        self,
        *,
        metrics: MetricsRecorder | None = None,
        tracing: TraceRecorder | None = None,
        events: StructuredEventSink | None = None,
    ) -> None:
        self.metrics = metrics or NoOpMetricsRecorder()
        self.tracing = tracing or NoOpTraceRecorder()
        self.events = events or NoOpStructuredEventSink()


__all__ = [
    "MetricsRecorder",
    "NoOpMetricsRecorder",
    "NoOpStructuredEventSink",
    "NoOpTraceRecorder",
    "Observability",
    "ObservationContext",
    "StructuredEventSink",
    "StructuredObservationEvent",
    "TraceRecorder",
    "TraceSpan",
]
