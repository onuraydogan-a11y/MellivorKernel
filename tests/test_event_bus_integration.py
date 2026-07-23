"""Integration test: ExecutionEngine and AuthorizationEngine publishing to a
real InMemoryEventBus, wired through a bootstrapped runtime.

Proves the full lifecycle sequence for both the tool and provider paths,
and that authorization/execution events correlate via `request_id`,
entirely through already-public APIs.
"""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.authorization import (
    AuthorizationDenied,
    AuthorizationEngine,
    AuthorizationGranted,
    PermissionResolver,
)
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
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
)


class _EchoProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "echo-provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echoed": dict(request)}


class _Recorder:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


def _subscribe_everything(bus: InMemoryEventBus, recorder: _Recorder) -> None:
    for event_type in (
        ExecutionStarted,
        ExecutionCompleted,
        ExecutionFailed,
        AuthorizationGranted,
        AuthorizationDenied,
    ):
        bus.subscribe(event_type, recorder)


def test_permissioned_tool_denied_then_granted_publishes_the_full_sequence() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    recorder = _Recorder()
    _subscribe_everything(bus, recorder)

    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry), event_bus=bus)
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        authorizer=authorizer,
        event_bus=bus,
    )
    context = runtime.execution_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    denied_result = engine.execute(request, context)
    granted_result = engine.execute(
        request, context, granted_permissions=frozenset({"kernel.internal"})
    )

    assert denied_result.success is False
    assert granted_result.success is True

    denied_sequence = [type(event).__name__ for event in recorder.events[:3]]
    granted_sequence = [type(event).__name__ for event in recorder.events[3:]]
    assert denied_sequence == ["ExecutionStarted", "AuthorizationDenied", "ExecutionFailed"]
    assert granted_sequence == ["ExecutionStarted", "AuthorizationGranted", "ExecutionCompleted"]

    # Every event in the denied sequence correlates via the same request_id,
    # and likewise for the granted sequence -- proving cross-subsystem
    # correlation works without either engine depending on the other's types.
    denied_ids = {event.request_id for event in recorder.events[:3]}  # type: ignore[attr-defined]
    granted_ids = {event.request_id for event in recorder.events[3:]}  # type: ignore[attr-defined]
    assert len(denied_ids) == 1
    assert len(granted_ids) == 1


def test_provider_path_publishes_execution_events_and_a_trivial_grant() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_EchoProvider(ProviderConfiguration(provider_name="echo-provider")))
    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    bus = InMemoryEventBus()
    recorder = _Recorder()
    _subscribe_everything(bus, recorder)

    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry), event_bus=bus)
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        authorizer=authorizer,
        event_bus=bus,
    )
    request = ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="echo-provider")

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    sequence = [type(event).__name__ for event in recorder.events]
    assert sequence == ["ExecutionStarted", "AuthorizationGranted", "ExecutionCompleted"]


def test_unsubscribing_stops_further_events_without_touching_the_engines() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    recorder = _Recorder()
    registration = bus.subscribe(ExecutionStarted, recorder)

    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), event_bus=bus
    )
    context = runtime.execution_context()

    engine.execute(ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), context)
    bus.unsubscribe(registration)
    engine.execute(ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), context)

    assert len(recorder.events) == 1
