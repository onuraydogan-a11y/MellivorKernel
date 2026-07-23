from __future__ import annotations

from mellivor_kernel.observability import (
    NoOpMetricsRecorder,
    NoOpStructuredEventSink,
    NoOpTraceRecorder,
    Observability,
    ObservationContext,
    StructuredObservationEvent,
)


def test_observation_context_mints_correlation_id() -> None:
    context = ObservationContext.new()

    assert context.correlation_id
    assert context.trace_id is None
    assert context.span_id is None


def test_observability_wires_noop_dependencies() -> None:
    observability = Observability(
        metrics=NoOpMetricsRecorder(),
        tracing=NoOpTraceRecorder(),
        events=NoOpStructuredEventSink(),
    )
    context = ObservationContext.new(correlation_id="corr-123")

    observability.metrics.increment("requests", value=1.0, context=context)
    span = observability.tracing.start_span("execute", context=context)
    span.end()
    observability.events.emit(
        StructuredObservationEvent(
            name="request.completed",
            message="request finished",
            context=context,
            attributes={"status": "ok"},
        )
    )

    assert span is not None
    assert context.correlation_id == "corr-123"


def test_structured_event_is_serializable_to_dict() -> None:
    context = ObservationContext.new(correlation_id="corr-456")
    event = StructuredObservationEvent(
        name="kernel.started",
        message="kernel initialized",
        context=context,
        attributes={"component": "bootstrap"},
    )

    assert event.to_dict()["name"] == "kernel.started"
    assert event.to_dict()["context"]["correlation_id"] == "corr-456"
