"""Tests for mellivor_kernel.execution.engine."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.events import Event, EventHandler, EventRegistration
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionCompleted,
    ExecutionContext,
    ExecutionEngine,
    ExecutionFailed,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStarted,
    ExecutionTarget,
)
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


@dataclass(frozen=True)
class _FakeOutcome:
    """A minimal object satisfying `AuthorizationOutcome` structurally,
    deliberately not the real `authorization` package -- proving
    `ExecutionEngine` only depends on the Protocol shape.
    """

    granted: bool
    reason: str | None = None


class _FakeAuthorizer:
    """A minimal object satisfying `Authorizer` structurally."""

    def __init__(self, *, granted: bool, reason: str | None = None) -> None:
        self._granted = granted
        self._reason = reason
        self.calls = 0

    def check(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str],
    ) -> _FakeOutcome:
        self.calls += 1
        return _FakeOutcome(granted=self._granted, reason=self._reason)


class _RecordingDispatcher(Dispatcher):
    """Records whether `dispatch` was ever called, to prove a denial
    short-circuits before reaching the dispatcher.
    """

    def __init__(self, tool_registry: ToolRegistry, provider_registry: ProviderRegistry) -> None:
        super().__init__(tool_registry, provider_registry)
        self.dispatched = False

    def dispatch(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult:
        self.dispatched = True
        return super().dispatch(request, context, granted_permissions=granted_permissions)


class _RecordingEventBus:
    """A minimal object satisfying `EventBus` structurally, deliberately not
    `InMemoryEventBus` -- proving `ExecutionEngine` only depends on the
    Protocol shape.
    """

    def __init__(self) -> None:
        self.published: list[Event] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration:
        raise NotImplementedError

    def unsubscribe(self, registration: EventRegistration) -> None:
        raise NotImplementedError


def _make_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_engine"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def _make_engine(*, register_echo: bool = True) -> ExecutionEngine:
    tool_registry = ToolRegistry()
    if register_echo:
        tool_registry.register(EchoTool())
    dispatcher = Dispatcher(tool_registry, ProviderRegistry())
    return ExecutionEngine(dispatcher)


def test_engine_executes_successful_tool_request() -> None:
    engine = _make_engine()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = engine.execute(request, _make_context())

    assert result.success is True
    assert result.payload == {"x": 1}


def test_engine_returns_failed_result_for_unregistered_operation() -> None:
    engine = _make_engine(register_echo=False)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.execute(request, _make_context())

    assert result.success is False
    assert result.error is not None


def test_engine_is_the_single_entry_point_regardless_of_target() -> None:
    engine = _make_engine()
    context = _make_context()

    tool_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), context
    )
    provider_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="missing"), context
    )

    assert tool_result.metadata["target"] == "tool"
    assert provider_result.metadata["target"] == "provider"
    assert provider_result.success is False


def test_engine_without_an_authorizer_behaves_exactly_as_before() -> None:
    """No authorizer configured: identical to this engine's pre-Sprint-8
    behavior -- no gate, dispatch always runs.
    """
    engine = _make_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1}),
        _make_context(),
    )

    assert result.success is True


def test_engine_dispatches_when_authorizer_grants() -> None:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    dispatcher = _RecordingDispatcher(tool_registry, ProviderRegistry())
    authorizer = _FakeAuthorizer(granted=True)
    engine = ExecutionEngine(dispatcher, authorizer=authorizer)

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1}),
        _make_context(),
        granted_permissions=frozenset({"kernel.internal"}),
    )

    assert authorizer.calls == 1
    assert dispatcher.dispatched is True
    assert result.success is True
    assert result.payload == {"x": 1}


def test_engine_never_dispatches_when_authorizer_denies() -> None:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    dispatcher = _RecordingDispatcher(tool_registry, ProviderRegistry())
    authorizer = _FakeAuthorizer(granted=False, reason="denied by policy")
    engine = ExecutionEngine(dispatcher, authorizer=authorizer)

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), _make_context()
    )

    assert authorizer.calls == 1
    assert dispatcher.dispatched is False
    assert result.success is False
    assert result.error == "denied by policy"
    assert result.metadata["stage"] == "authorization"


def test_engine_uses_default_reason_when_authorizer_omits_one() -> None:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    dispatcher = _RecordingDispatcher(tool_registry, ProviderRegistry())
    authorizer = _FakeAuthorizer(granted=False, reason=None)
    engine = ExecutionEngine(dispatcher, authorizer=authorizer)

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), _make_context()
    )

    assert result.success is False
    assert result.error == "Authorization denied."


def test_engine_without_an_event_bus_publishes_nothing() -> None:
    """No event bus configured: identical to this engine's pre-Sprint-9
    behavior -- no events, no error.
    """
    engine = _make_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), _make_context()
    )

    assert result.success is True  # no event bus wired in, nothing to assert on it


def test_engine_publishes_started_then_completed_on_success() -> None:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    dispatcher = Dispatcher(tool_registry, ProviderRegistry())
    event_bus = _RecordingEventBus()
    engine = ExecutionEngine(dispatcher, event_bus=event_bus)

    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})
    engine.execute(request, _make_context())

    assert [type(event) for event in event_bus.published] == [
        ExecutionStarted,
        ExecutionCompleted,
    ]
    started, completed = event_bus.published
    assert isinstance(started, ExecutionStarted)
    assert isinstance(completed, ExecutionCompleted)
    assert started.request_id == request.request_id == completed.request_id
    assert started.operation == "echo"
    assert completed.execution_time_seconds >= 0.0


def test_engine_publishes_started_then_failed_on_dispatch_failure() -> None:
    engine = _make_engine(register_echo=False)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")
    event_bus = _RecordingEventBus()
    dispatcher = Dispatcher(ToolRegistry(), ProviderRegistry())
    engine = ExecutionEngine(dispatcher, event_bus=event_bus)

    engine.execute(request, _make_context())

    assert [type(event) for event in event_bus.published] == [ExecutionStarted, ExecutionFailed]
    failed = event_bus.published[1]
    assert isinstance(failed, ExecutionFailed)
    assert failed.error is not None
    assert failed.stage is None


def test_engine_publishes_failed_with_authorization_stage_on_denial() -> None:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    dispatcher = Dispatcher(tool_registry, ProviderRegistry())
    event_bus = _RecordingEventBus()
    authorizer = _FakeAuthorizer(granted=False, reason="denied by policy")
    engine = ExecutionEngine(dispatcher, authorizer=authorizer, event_bus=event_bus)

    engine.execute(ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), _make_context())

    assert [type(event) for event in event_bus.published] == [ExecutionStarted, ExecutionFailed]
    failed = event_bus.published[1]
    assert isinstance(failed, ExecutionFailed)
    assert failed.stage == "authorization"
    assert failed.error == "denied by policy"
