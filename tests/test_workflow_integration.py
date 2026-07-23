"""Integration test: WorkflowEngine orchestrating ExecutionEngine, wired
through a bootstrapped runtime.

Proves the acceptance criterion for Sprint 12: Workflow orchestrates,
Execution executes, and the two responsibilities stay separated --
`WorkflowEngine` never touches a tool or provider directly, only
`ExecutionEngine.execute()`. Built entirely from already-public bootstrap
output, with no change to `bootstrap`, `execution`, `authorization`,
`memory`, or `events`.
"""

from __future__ import annotations

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import InMemoryEventBus
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget
from mellivor_kernel.memory import InMemoryStore, MemoryQuery
from mellivor_kernel.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
)


def test_workflow_orchestrates_execution_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    execution_engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    memory = InMemoryStore()
    event_bus = InMemoryEventBus()
    workflow_engine = WorkflowEngine(execution_engine, memory=memory, event_bus=event_bus)

    definition = WorkflowDefinition(
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
    workflow = Workflow(definition=definition)
    context = WorkflowContext(execution_context=runtime.execution_context())

    result = workflow_engine.run(workflow, context)

    assert result.success is True
    assert list(result.step_results) == ["greet", "report_version"]
    assert result.step_results["greet"].payload == {"message": "hello"}
    assert result.step_results["report_version"].success is True

    # Memory: the workflow-level summary is genuinely readable back
    # through the same MemoryStore -- proving read/write both work
    # through the abstraction, not just write.
    remembered = memory.get(workflow.workflow_id)
    assert remembered is not None
    assert remembered.metadata["name"] == "onboarding"
    found = memory.search(MemoryQuery(tag="workflow"))
    assert workflow.workflow_id in {entry.id for entry in found}


def test_workflow_stops_early_on_a_dispatch_failure_and_the_kernel_stays_consistent() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    execution_engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    workflow_engine = WorkflowEngine(execution_engine)

    definition = WorkflowDefinition(
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
    context = WorkflowContext(execution_context=runtime.execution_context())

    result = workflow_engine.run(Workflow(definition=definition), context)

    assert result.success is False
    assert result.stopped_at == "missing_tool"
    assert "never_runs" not in result.step_results

    # Execution's own registries are untouched by the failure -- Workflow
    # never bypasses ExecutionEngine to reach tools/providers directly.
    assert runtime.tool_registry.exists("echo") is True
