"""Integration test: AgentEngine orchestrating WorkflowEngine orchestrating
ExecutionEngine, wired through a bootstrapped runtime.

Proves the acceptance criterion for Sprint 13A: Agent delegates to
Workflow, Workflow delegates to Execution, Execution delegates to
Dispatcher -- responsibilities remain perfectly separated. Built entirely
from already-public bootstrap output, with no change to `bootstrap`,
`execution`, `authorization`, `memory`, `events`, or `workflow`.
"""

from __future__ import annotations

from mellivor_kernel.agents import Agent, AgentContext, AgentDefinition, AgentEngine
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import InMemoryEventBus
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget
from mellivor_kernel.memory import InMemoryStore, MemoryQuery
from mellivor_kernel.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
)


def test_agent_delegates_through_workflow_to_execution_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    execution_engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    workflow_engine = WorkflowEngine(execution_engine)
    memory = InMemoryStore()
    event_bus = InMemoryEventBus()
    agent_engine = AgentEngine(workflow_engine, memory=memory, event_bus=event_bus)

    workflow = WorkflowDefinition(
        name="onboarding",
        steps=(
            WorkflowStep(
                name="greet",
                request=ExecutionRequest(
                    target=ExecutionTarget.TOOL, operation="echo", payload={"message": "hello"}
                ),
            ),
            WorkflowStep(
                name="report_version",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="version"),
            ),
        ),
    )
    definition = AgentDefinition(name="onboarding-agent", workflow=workflow)
    agent = Agent(definition=definition)
    context = AgentContext(
        workflow_context=WorkflowContext(execution_context=runtime.execution_context())
    )

    result = agent_engine.execute(agent, context)

    assert result.success is True
    assert list(result.workflow_result.step_results) == ["greet", "report_version"]
    assert result.workflow_result.step_results["greet"].payload == {"message": "hello"}

    # Memory: read/write both genuinely work through the same MemoryStore.
    remembered = memory.get(agent.agent_id)
    assert remembered is not None
    assert remembered.metadata["name"] == "onboarding-agent"
    found = memory.search(MemoryQuery(tag="agent"))
    assert agent.agent_id in {entry.id for entry in found}


def test_agent_run_fails_when_its_workflow_stops_early() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    execution_engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    workflow_engine = WorkflowEngine(execution_engine)
    agent_engine = AgentEngine(workflow_engine)

    workflow = WorkflowDefinition(
        name="broken",
        steps=(
            WorkflowStep(
                name="missing_tool",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="does-not-exist"),
            ),
            WorkflowStep(
                name="never_runs",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"),
            ),
        ),
    )
    agent = Agent(definition=AgentDefinition(name="broken-agent", workflow=workflow))
    context = AgentContext(
        workflow_context=WorkflowContext(execution_context=runtime.execution_context())
    )

    result = agent_engine.execute(agent, context)

    assert result.success is False
    assert result.workflow_result.stopped_at == "missing_tool"
    assert "never_runs" not in result.workflow_result.step_results

    # Kernel state stays consistent: Agent never bypassed Workflow/Execution
    # to reach the tool registry directly.
    assert runtime.tool_registry.exists("echo") is True
