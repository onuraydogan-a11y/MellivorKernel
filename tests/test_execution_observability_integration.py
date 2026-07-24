"""Integration test: ExecutionEngine emitting to observability.StructuredEventSink
and events.EventBus side by side, wired through a bootstrapped runtime.

Sprint 17 (Foundation Adoption): proves the observability foundation
(ADR-0013) is consumable by a real subsystem, not just its own foundation
tests -- built entirely from already-public bootstrap output, with no
change to `bootstrap`, `tools`, or `providers`.
"""

from __future__ import annotations

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import Event, InMemoryEventBus
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionCompleted,
    ExecutionEngine,
    ExecutionFailed,
    ExecutionRequest,
    ExecutionStarted,
    ExecutionTarget,
)
from mellivor_kernel.observability import StructuredObservationEvent


class _EventRecorder:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


class _ObservabilityRecorder:
    def __init__(self) -> None:
        self.emitted: list[StructuredObservationEvent] = []

    def emit(self, event: object) -> None:
        assert isinstance(event, StructuredObservationEvent)
        self.emitted.append(event)


def test_execution_emits_to_event_bus_and_observability_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    recorder = _EventRecorder()
    for event_type in (ExecutionStarted, ExecutionCompleted, ExecutionFailed):
        bus.subscribe(event_type, recorder)
    observability = _ObservabilityRecorder()

    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        event_bus=bus,
        observability=observability,
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True

    # Both mechanisms saw the same two lifecycle points for the same request.
    assert [type(event).__name__ for event in recorder.events] == [
        "ExecutionStarted",
        "ExecutionCompleted",
    ]
    assert [event.name for event in observability.emitted] == [
        "execution.started",
        "execution.completed",
    ]
    bus_request_ids = {event.request_id for event in recorder.events}  # type: ignore[attr-defined]
    observability_correlation_ids = {
        event.context.correlation_id for event in observability.emitted
    }
    assert bus_request_ids == observability_correlation_ids == {request.request_id}


def test_execution_failure_emits_to_both_mechanisms_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).build()

    bus = InMemoryEventBus()
    recorder = _EventRecorder()
    for event_type in (ExecutionStarted, ExecutionCompleted, ExecutionFailed):
        bus.subscribe(event_type, recorder)
    observability = _ObservabilityRecorder()

    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        event_bus=bus,
        observability=observability,
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="does-not-exist")

    result = engine.execute(request, runtime.execution_context())

    assert result.success is False
    assert [type(event).__name__ for event in recorder.events] == [
        "ExecutionStarted",
        "ExecutionFailed",
    ]
    assert [event.name for event in observability.emitted] == [
        "execution.started",
        "execution.failed",
    ]
    assert observability.emitted[1].attributes["error"] is not None


def test_execution_with_only_observability_configured_leaves_event_bus_untouched() -> None:
    """Configuring `observability` alone must not change `EventBus`
    behavior -- the two mechanisms are independent, not coupled.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    observability = _ObservabilityRecorder()
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        observability=observability,
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert [event.name for event in observability.emitted] == [
        "execution.started",
        "execution.completed",
    ]
