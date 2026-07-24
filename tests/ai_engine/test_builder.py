"""Tests for mellivor_kernel.ai_engine.builder.AIEngineBuilder."""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from mellivor_kernel.ai_engine import AIEngine, AIEngineBuilder, AIEngineError
from mellivor_kernel.authorization import AuthorizationDenied, AuthorizationGranted
from mellivor_kernel.bootstrap import BootstrapBuilder, RuntimeContext
from mellivor_kernel.config import load_config
from mellivor_kernel.events import Event, InMemoryEventBus
from mellivor_kernel.execution import ExecutionContext, ExecutionRequest, ExecutionTarget
from mellivor_kernel.memory import InMemoryStore
from mellivor_kernel.plugins import Plugin, PluginContext, PluginMetadata, PluginRegistry


def _make_runtime() -> RuntimeContext:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    return BootstrapBuilder(config).with_builtin_tools().build()


def _health_check_request() -> ExecutionRequest:
    return ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")


def test_build_with_no_options_produces_a_minimal_engine() -> None:
    runtime = _make_runtime()

    engine = AIEngineBuilder(runtime).build()

    assert isinstance(engine, AIEngine)
    assert engine.plugin_registry.enumerate() == ()


class _RecordingHandler:
    """A handler satisfying `EventHandler` structurally: just records."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


def test_build_with_no_authorization_requested_never_consults_an_authorizer() -> None:
    """No `.authorizer` accessor exists to introspect wiring directly, so
    this proves the absence of an `AuthorizationEngine` behaviorally:
    `ExecutionEngine.execute()` ignores `granted_permissions` entirely
    when no authorizer is configured (per its own contract) -- so a
    permissioned tool fails even when granted the exact permission it
    requires, and no `AuthorizationGranted`/`AuthorizationDenied` event is
    ever published, since nothing consulted an `Authorizer` at all.
    """
    event_bus = InMemoryEventBus()
    handler = _RecordingHandler()
    event_bus.subscribe(AuthorizationGranted, handler)
    event_bus.subscribe(AuthorizationDenied, handler)
    engine = AIEngineBuilder(_make_runtime()).with_event_bus(event_bus).build()

    result = engine.execute(
        _health_check_request(),
        engine.execution_context(),
        granted_permissions=frozenset({"kernel.internal"}),
    )

    assert result.success is False
    assert handler.events == []


def test_with_authorization_builds_a_default_authorization_engine() -> None:
    """Proves a real, permission-enforcing `AuthorizationEngine` was built
    -- behaviorally, since `AIEngine` exposes no `.authorizer` accessor to
    inspect directly.
    """
    engine = AIEngineBuilder(_make_runtime()).with_authorization().build()

    denied = engine.execute(_health_check_request(), engine.execution_context())
    assert denied.success is False

    granted = engine.execute(
        _health_check_request(),
        engine.execution_context(),
        granted_permissions=frozenset({"kernel.internal"}),
    )
    assert granted.success is True


def test_with_authorization_accepts_a_custom_authorizer() -> None:
    """Proves the exact authorizer instance passed to `with_authorization()`
    -- not a freshly built default -- is what `execute()` consults: a
    permission-free tool (`echo`) that a default `AuthorizationEngine`
    would allow is denied here, because the wired-in authorizer always
    denies.
    """
    runtime = _make_runtime()
    custom = _RejectingAuthorizer()
    engine = AIEngineBuilder(runtime).with_authorization(custom).build()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"msg": "hi"})

    result = engine.execute(request, engine.execution_context())

    assert result.success is False
    assert result.error == "rejected by test authorizer"


def test_with_authorization_before_or_after_event_bus_is_order_independent() -> None:
    runtime_a = _make_runtime()
    bus_a = InMemoryEventBus()
    engine_a = AIEngineBuilder(runtime_a).with_event_bus(bus_a).with_authorization().build()

    runtime_b = _make_runtime()
    bus_b = InMemoryEventBus()
    engine_b = AIEngineBuilder(runtime_b).with_authorization().with_event_bus(bus_b).build()

    for engine in (engine_a, engine_b):
        denied = engine.execute(_health_check_request(), engine.execution_context())
        assert denied.success is False
        granted = engine.execute(
            _health_check_request(),
            engine.execution_context(),
            granted_permissions=frozenset({"kernel.internal"}),
        )
        assert granted.success is True


def test_with_plugin_registry_uses_the_supplied_instance() -> None:
    runtime = _make_runtime()
    registry = PluginRegistry()

    engine = AIEngineBuilder(runtime).with_plugin_registry(registry).build()

    assert engine.plugin_registry is registry


def test_build_without_plugin_registry_creates_an_empty_one() -> None:
    runtime = _make_runtime()

    engine = AIEngineBuilder(runtime).build()

    assert engine.plugin_registry.enumerate() == ()


def test_with_plugin_discovery_populates_the_registry(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "fake"
    plugin_dir.mkdir()
    (plugin_dir / "plugin_manifest.json").write_text(
        json.dumps(
            {
                "id": "fake",
                "name": "Fake",
                "version": "1.0.0",
                "author": "Test",
                "entry_point": "tests.ai_engine.test_builder:_DiscoverablePlugin",
            }
        ),
        encoding="utf-8",
    )
    runtime = _make_runtime()

    engine = AIEngineBuilder(runtime).with_plugin_discovery(tmp_path).build()

    assert [m.id for m in engine.plugin_registry.enumerate()] == ["fake"]


def test_with_plugin_discovery_wraps_a_failure_in_ai_engine_error(tmp_path: Path) -> None:
    runtime = _make_runtime()

    with pytest.raises(AIEngineError):
        AIEngineBuilder(runtime).with_plugin_discovery(tmp_path / "does-not-exist").build()


def test_with_memory_and_observability_are_accepted() -> None:
    runtime = _make_runtime()
    memory = InMemoryStore()

    engine = AIEngineBuilder(runtime).with_memory(memory).build()

    assert isinstance(engine, AIEngine)


def test_build_returns_a_new_engine_each_call() -> None:
    runtime = _make_runtime()
    builder = AIEngineBuilder(runtime)

    first = builder.build()
    second = builder.build()

    assert first is not second


def test_build_with_a_registry_already_owned_by_a_live_engine_raises() -> None:
    registry = PluginRegistry()
    first = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    with pytest.raises(AIEngineError):
        AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    # `first` must stay referenced (and therefore live) for the assertion
    # above to be meaningful -- this line also guards against an
    # over-eager linter deciding `first` is unused.
    assert first.plugin_registry is registry


def test_build_with_a_registry_whose_previous_owner_was_collected_succeeds() -> None:
    registry = PluginRegistry()
    first = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()
    del first
    gc.collect()

    second = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    assert second.plugin_registry is registry


@dataclass(frozen=True)
class _FakeOutcome:
    """A minimal object satisfying `AuthorizationOutcome` structurally."""

    granted: bool
    reason: str | None = None


class _RejectingAuthorizer:
    """A minimal object satisfying `Authorizer` structurally: always denies,
    to prove the exact authorizer instance passed to `with_authorization()`
    is the one `execute()` actually consults.
    """

    def check(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str],
    ) -> _FakeOutcome:
        return _FakeOutcome(granted=False, reason="rejected by test authorizer")


class _DiscoverablePlugin(Plugin):
    """A minimal, module-level `Plugin` importable by `resolve_entry_point()`."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id="fake", name="Fake", version="1.0.0", description="")

    def initialize(self, context: PluginContext) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass
