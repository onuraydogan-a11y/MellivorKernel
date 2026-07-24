"""Tests for mellivor_kernel.ai_engine.engine.

Covers `AIEngine`'s properties, its three delegated operations
(`execute()`/`run_workflow()`/`run_agent()`), its context-builder methods,
and its plugin-lifecycle management (`start_plugins()`/`stop_plugins()`/
`dispose_plugins()`).
"""

from __future__ import annotations

from mellivor_kernel.agents import Agent, AgentContext, AgentDefinition
from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder, RuntimeContext
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import ExecutionContext, ExecutionRequest, ExecutionTarget
from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginLifecycleState,
    PluginMetadata,
    PluginRegistry,
)
from mellivor_kernel.workflow import Workflow, WorkflowContext, WorkflowDefinition, WorkflowStep


def _make_runtime() -> RuntimeContext:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    return BootstrapBuilder(config).with_builtin_tools().build()


def _greeting_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="greet",
        steps=(
            WorkflowStep(
                name="say-hi",
                request=ExecutionRequest(
                    target=ExecutionTarget.TOOL, operation="echo", payload={"msg": "hi"}
                ),
            ),
        ),
    )


class _RecordingPlugin(Plugin):
    """A minimal plugin recording every lifecycle call it receives."""

    def __init__(self, plugin_id: str = "recording") -> None:
        self._plugin_id = plugin_id
        self.calls: list[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._plugin_id, name="Recording Plugin", version="1.0.0", description=""
        )

    def initialize(self, context: PluginContext) -> None:
        self.calls.append("initialize")

    def start(self) -> None:
        self.calls.append("start")

    def stop(self) -> None:
        self.calls.append("stop")

    def dispose(self) -> None:
        self.calls.append("dispose")


def test_runtime_property_returns_the_composed_runtime() -> None:
    runtime = _make_runtime()

    engine = AIEngineBuilder(runtime).build()

    assert engine.runtime is runtime


def test_execute_delegates_to_the_execution_engine() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"msg": "hi"})

    result = engine.execute(request, engine.execution_context())

    assert result.success is True
    assert result.payload == {"msg": "hi"}


def test_run_workflow_delegates_to_the_workflow_engine() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()
    workflow = Workflow(definition=_greeting_workflow())

    result = engine.run_workflow(workflow, engine.workflow_context())

    assert result.success is True
    assert result.step_results["say-hi"].payload == {"msg": "hi"}


def test_run_agent_delegates_to_the_agent_engine() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()
    agent = Agent(definition=AgentDefinition(name="greeter", workflow=_greeting_workflow()))

    result = engine.run_agent(agent, engine.agent_context())

    assert result.success is True
    assert result.workflow_result.step_results["say-hi"].payload == {"msg": "hi"}


def test_execution_context_builds_a_usable_execution_context() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()

    context = engine.execution_context()

    assert isinstance(context, ExecutionContext)
    assert context.runtime is engine.runtime.execution_context().runtime


def test_workflow_context_builds_a_usable_workflow_context() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()

    context = engine.workflow_context()

    assert isinstance(context, WorkflowContext)
    assert context.step_results == {}


def test_agent_context_builds_a_usable_agent_context() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()

    context = engine.agent_context()

    assert isinstance(context, AgentContext)


def test_plugin_context_builds_a_usable_plugin_context() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()

    context = engine.plugin_context()

    assert isinstance(context, PluginContext)


def test_start_plugins_initializes_and_starts_every_registered_plugin() -> None:
    registry = PluginRegistry()
    plugin = _RecordingPlugin()
    registry.register(plugin)
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    engine.start_plugins()

    assert plugin.calls == ["initialize", "start"]


def test_stop_plugins_stops_every_registered_plugin() -> None:
    registry = PluginRegistry()
    plugin = _RecordingPlugin()
    registry.register(plugin)
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()
    engine.start_plugins()

    engine.stop_plugins()

    assert plugin.calls == ["initialize", "start", "stop"]


def test_dispose_plugins_disposes_every_registered_plugin() -> None:
    registry = PluginRegistry()
    plugin = _RecordingPlugin()
    registry.register(plugin)
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()
    engine.start_plugins()
    engine.stop_plugins()

    engine.dispose_plugins()

    assert plugin.calls == ["initialize", "start", "stop", "dispose"]


def test_a_plugin_registered_after_construction_is_still_picked_up() -> None:
    registry = PluginRegistry()
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()
    plugin = _RecordingPlugin()
    registry.register(plugin)

    engine.start_plugins()

    assert plugin.calls == ["initialize", "start"]


def test_the_same_plugin_lifecycle_instance_is_reused_across_calls() -> None:
    registry = PluginRegistry()
    plugin = _RecordingPlugin()
    registry.register(plugin)
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    engine.start_plugins()
    engine.stop_plugins()
    engine.start_plugins()

    # A fresh `PluginLifecycle` per call would raise on `initialize()` from
    # a non-REGISTERED state (see `mellivor_kernel.plugins.PluginLifecycle`)
    # -- reaching RUNNING again here proves the same instance was reused.
    assert plugin.calls == ["initialize", "start", "stop", "start"]


def test_start_plugins_with_an_empty_registry_does_nothing() -> None:
    engine = AIEngineBuilder(_make_runtime()).build()

    engine.start_plugins()  # must not raise

    assert engine.plugin_registry.enumerate() == ()


def test_lifecycle_state_reflects_start_stop_dispose_sequence() -> None:
    registry = PluginRegistry()
    plugin = _RecordingPlugin()
    registry.register(plugin)
    engine = AIEngineBuilder(_make_runtime()).with_plugin_registry(registry).build()

    engine.start_plugins()
    assert engine._lifecycle_for("recording").state == PluginLifecycleState.RUNNING

    engine.stop_plugins()
    assert engine._lifecycle_for("recording").state == PluginLifecycleState.STOPPED

    engine.dispose_plugins()
    assert engine._lifecycle_for("recording").state == PluginLifecycleState.DISPOSED
