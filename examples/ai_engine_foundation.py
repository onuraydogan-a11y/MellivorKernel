"""End-to-end example: the AI Engine Foundation.

Assembles a bootstrapped `RuntimeContext` into a full orchestration chain
(`ExecutionEngine` -> `WorkflowEngine` -> `AgentEngine`, with an
`AuthorizationEngine` consulted and an `InMemoryEventBus`/`InMemoryStore`
attached) through `AIEngineBuilder` alone -- no `Dispatcher`,
`ExecutionEngine`, `WorkflowEngine`, or `AgentEngine` constructed by hand
here, unlike every example before Sprint 22. Also discovers and runs the
already-shipped `system-info` sample plugin
(`examples/sample_plugins/system-info/`) through
`with_plugin_discovery()`.

Run directly: `python examples/ai_engine_foundation.py`
"""

from __future__ import annotations

from pathlib import Path

from mellivor_kernel.agents import Agent, AgentCompleted, AgentDefinition, AgentStarted
from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import Event, InMemoryEventBus
from mellivor_kernel.execution import (
    ExecutionCompleted,
    ExecutionRequest,
    ExecutionStarted,
    ExecutionTarget,
)
from mellivor_kernel.memory import InMemoryStore
from mellivor_kernel.workflow import (
    Workflow,
    WorkflowCompleted,
    WorkflowDefinition,
    WorkflowStarted,
    WorkflowStep,
)


class _PrintingHandler:
    """A handler satisfying `EventHandler` structurally: just prints."""

    def handle(self, event: Event) -> None:
        print(f"    event: {type(event).__name__}")


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "WARNING"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    event_bus = InMemoryEventBus()
    handler = _PrintingHandler()
    for event_type in (
        ExecutionStarted,
        ExecutionCompleted,
        WorkflowStarted,
        WorkflowCompleted,
        AgentStarted,
        AgentCompleted,
    ):
        event_bus.subscribe(event_type, handler)
    memory = InMemoryStore()

    engine = (
        AIEngineBuilder(runtime)
        .with_authorization()
        .with_event_bus(event_bus)
        .with_memory(memory)
        .with_plugin_discovery(Path(__file__).parent / "sample_plugins")
        .build()
    )

    print("execute() -- ExecutionEngine:")
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"msg": "hi"})
    execution_result = engine.execute(request, engine.execution_context())
    print(f"    success: {execution_result.success}, payload: {execution_result.payload}")

    print("run_workflow() -- WorkflowEngine:")
    workflow_definition = WorkflowDefinition(
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
    workflow_result = engine.run_workflow(
        Workflow(definition=workflow_definition), engine.workflow_context()
    )
    print(f"    success: {workflow_result.success}")

    print("run_agent() -- AgentEngine:")
    agent = Agent(definition=AgentDefinition(name="greeter", workflow=workflow_definition))
    agent_result = engine.run_agent(agent, engine.agent_context())
    print(f"    success: {agent_result.success}")
    print(f"    recorded to memory: {memory.get(agent.agent_id) is not None}")

    print("plugin discovery + lifecycle:")
    print(f"    discovered: {[m.id for m in engine.plugin_registry.enumerate()]}")
    engine.start_plugins()
    plugin = engine.plugin_registry.lookup("system-info")
    snapshot = plugin.collect()  # type: ignore[attr-defined]
    print(f"    kernel_version:   {snapshot.kernel_version}")
    print(f"    registered_tools: {snapshot.registered_tools}")
    engine.stop_plugins()
    engine.dispose_plugins()


if __name__ == "__main__":
    main()
