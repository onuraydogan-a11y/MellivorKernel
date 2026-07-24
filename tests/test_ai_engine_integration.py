"""End-to-end test: the AI Engine Foundation composing a real bootstrapped
runtime into a full orchestration chain (`ExecutionEngine` -> `WorkflowEngine`
-> `AgentEngine`, with authorization/events/memory attached) plus real
plugin discovery and lifecycle, using the already-shipped `SystemInfoPlugin`
(Sprint 20) from `examples/sample_plugins/system-info/`.

Mirrors `tests/test_plugin_discovery_integration.py`'s end-to-end style,
exercised here through `AIEngineBuilder`/`AIEngine` instead of wiring each
subsystem by hand -- proving Sprint 22's composition layer produces exactly
the same real behavior as assembling `bootstrap` + the orchestration-chain
engines + `plugin_discovery` manually would.
"""

from __future__ import annotations

import json
from pathlib import Path

from mellivor_kernel.agents import Agent, AgentDefinition
from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import InMemoryEventBus
from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.memory import InMemoryStore
from mellivor_kernel.plugins_builtin import SystemInfoPlugin
from mellivor_kernel.version import __version__
from mellivor_kernel.workflow import Workflow, WorkflowDefinition, WorkflowStep


def _write_system_info_manifest(root: Path) -> None:
    plugin_dir = root / "system-info"
    plugin_dir.mkdir(parents=True)
    manifest = {
        "id": "system-info",
        "name": "System Information Plugin",
        "version": "1.0.0",
        "description": "Exposes read-only kernel information.",
        "author": "Mellivor Kernel",
        "minimum_kernel_version": __version__,
        "capabilities": [
            {
                "name": "kernel.introspection",
                "description": "Read-only kernel and runtime information.",
            }
        ],
        "entry_point": "mellivor_kernel.plugins_builtin.system_info:SystemInfoPlugin",
    }
    (plugin_dir / "plugin_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


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


def test_ai_engine_end_to_end_orchestration_chain() -> None:
    """Full chain: bootstrap -> AIEngineBuilder(auth+events+memory) ->
    execute()/run_workflow()/run_agent(), each proven with real objects.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()
    event_bus = InMemoryEventBus()
    memory = InMemoryStore()

    engine = (
        AIEngineBuilder(runtime)
        .with_authorization()
        .with_event_bus(event_bus)
        .with_memory(memory)
        .build()
    )

    # `AIEngine` exposes no `.authorizer` accessor -- prove authorization
    # was actually wired in behaviorally: a permissioned tool is denied
    # without the right permission and succeeds once granted.
    health_check = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")
    denied = engine.execute(health_check, engine.execution_context())
    assert denied.success is False
    granted = engine.execute(
        health_check,
        engine.execution_context(),
        granted_permissions=frozenset({"kernel.internal"}),
    )
    assert granted.success is True

    # 1. execute() -- ExecutionEngine
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"msg": "hi"})
    execution_result = engine.execute(request, engine.execution_context())
    assert execution_result.success is True
    assert execution_result.payload == {"msg": "hi"}

    # 2. run_workflow() -- WorkflowEngine
    workflow = Workflow(definition=_greeting_workflow())
    workflow_result = engine.run_workflow(workflow, engine.workflow_context())
    assert workflow_result.success is True
    assert workflow_result.step_results["say-hi"].payload == {"msg": "hi"}

    # 3. run_agent() -- AgentEngine
    agent = Agent(definition=AgentDefinition(name="greeter", workflow=_greeting_workflow()))
    agent_result = engine.run_agent(agent, engine.agent_context())
    assert agent_result.success is True
    assert agent_result.workflow_result.step_results["say-hi"].payload == {"msg": "hi"}

    # Every run was recorded to the shared memory store.
    assert memory.get(agent.agent_id) is not None


def test_ai_engine_discovers_and_runs_the_real_system_info_plugin(tmp_path: Path) -> None:
    """Full chain: bootstrap -> AIEngineBuilder.with_plugin_discovery() ->
    start_plugins() -> the real, already-shipped `SystemInfoPlugin` reports
    real providers/tools from the same runtime `AIEngine` composes on top of.
    """
    _write_system_info_manifest(tmp_path)
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    engine = AIEngineBuilder(runtime).with_plugin_discovery(tmp_path).build()

    assert [m.id for m in engine.plugin_registry.enumerate()] == ["system-info"]

    engine.start_plugins()

    plugin = engine.plugin_registry.lookup("system-info")
    assert isinstance(plugin, SystemInfoPlugin)

    snapshot = plugin.collect()
    assert snapshot.kernel_version == __version__
    assert "kernel.introspection" in snapshot.available_capabilities
    assert snapshot.registered_tools == ("echo", "health_check", "version")
    assert snapshot.runtime_health.healthy is True

    engine.stop_plugins()
    engine.dispose_plugins()
