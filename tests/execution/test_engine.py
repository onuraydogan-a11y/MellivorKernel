"""Tests for mellivor_kernel.execution.engine."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
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
