"""Tests for mellivor_kernel.workflow.engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.events import Event, EventHandler, EventRegistration
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.memory import InMemoryStore
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import BaseTool, ToolContext, ToolRegistry, ToolResult
from mellivor_kernel.tools.builtin import EchoTool
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.workflow import (
    Workflow,
    WorkflowCompleted,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowFailed,
    WorkflowStarted,
    WorkflowStep,
)


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


class _FailingTool(BaseTool):
    @property
    def id(self) -> str:
        return "always-fails"

    @property
    def name(self) -> str:
        return "Always Fails"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A tool that always raises."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        raise RuntimeError("this tool always fails")


class _RecordingEventBus:
    """A minimal object satisfying `EventBus` structurally."""

    def __init__(self) -> None:
        self.published: list[Event] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration:
        raise NotImplementedError

    def unsubscribe(self, registration: EventRegistration) -> None:
        raise NotImplementedError


def _make_context() -> WorkflowContext:
    settings = _FakeSettings()
    execution_context = ExecutionContext(
        configuration=settings,
        logger=get_logger("test_workflow_engine"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )
    return WorkflowContext(execution_context=execution_context)


def _make_execution_engine(*, with_failing_tool: bool = False) -> ExecutionEngine:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    if with_failing_tool:
        tool_registry.register(_FailingTool())
    return ExecutionEngine(Dispatcher(tool_registry, ProviderRegistry()))


def _step(
    name: str, *, operation: str = "echo", payload: Mapping[str, object] | None = None
) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL, operation=operation, payload=payload or {}
        ),
    )


def test_empty_workflow_succeeds_trivially() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    workflow = Workflow(definition=WorkflowDefinition(name="empty"))

    result = engine.run(workflow, _make_context())

    assert result.success is True
    assert dict(result.step_results) == {}
    assert result.stopped_at is None


def test_single_step_workflow() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="single", steps=(_step("only", payload={"x": 1}),))
    workflow = Workflow(definition=definition)

    result = engine.run(workflow, _make_context())

    assert result.success is True
    assert set(result.step_results) == {"only"}
    assert result.step_results["only"].payload == {"x": 1}


def test_sequential_multi_step_workflow_runs_every_step_in_order() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="multi",
        steps=(
            _step("first", payload={"n": 1}),
            _step("second", payload={"n": 2}),
            _step("third", payload={"n": 3}),
        ),
    )
    workflow = Workflow(definition=definition)

    result = engine.run(workflow, _make_context())

    assert result.success is True
    assert list(result.step_results) == ["first", "second", "third"]
    assert [r.payload for r in result.step_results.values()] == [{"n": 1}, {"n": 2}, {"n": 3}]


def test_workflow_failure_stops_and_reports_the_failing_step() -> None:
    engine = WorkflowEngine(_make_execution_engine(with_failing_tool=True))
    definition = WorkflowDefinition(name="failing", steps=(_step("bad", operation="always-fails"),))
    workflow = Workflow(definition=definition)

    result = engine.run(workflow, _make_context())

    assert result.success is False
    assert result.stopped_at == "bad"
    assert "bad" in (result.error or "")


def test_early_stop_prevents_later_steps_from_running() -> None:
    engine = WorkflowEngine(_make_execution_engine(with_failing_tool=True))
    definition = WorkflowDefinition(
        name="early-stop",
        steps=(
            _step("first", payload={"n": 1}),
            _step("fails", operation="always-fails"),
            _step("never-runs", payload={"n": 3}),
        ),
    )
    workflow = Workflow(definition=definition)

    result = engine.run(workflow, _make_context())

    assert result.success is False
    assert result.stopped_at == "fails"
    assert set(result.step_results) == {"first", "fails"}
    assert "never-runs" not in result.step_results


def test_continue_on_failure_lets_the_workflow_finish() -> None:
    engine = WorkflowEngine(_make_execution_engine(with_failing_tool=True))
    failing_step = WorkflowStep(
        name="fails",
        request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
        continue_on_failure=True,
    )
    definition = WorkflowDefinition(
        name="tolerant", steps=(failing_step, _step("after", payload={"n": 1}))
    )
    workflow = Workflow(definition=definition)

    result = engine.run(workflow, _make_context())

    assert result.success is True
    assert set(result.step_results) == {"fails", "after"}
    assert result.step_results["fails"].success is False
    assert result.step_results["after"].success is True


def test_shared_context_accumulates_step_results_as_the_workflow_progresses() -> None:
    """`WorkflowEngine` threads a new `WorkflowContext` between steps,
    with `step_results` updated to include every step completed so far --
    this is what "shared" means (a later step could inspect an earlier
    step's outcome). Proven here via the immutable-replace mechanics
    directly, since a static `WorkflowStep.request` has no way to observe
    it itself.
    """
    context = _make_context()
    assert dict(context.step_results) == {}

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="shared", steps=(_step("first", payload={"n": 1}), _step("second", payload={"n": 2}))
    )

    result = engine.run(Workflow(definition=definition), context)

    # The original context handed to `run()` is untouched (immutable) --
    # WorkflowEngine only ever threads a *new* context internally.
    assert dict(context.step_results) == {}
    # The final result reflects both steps having accumulated in order,
    # exactly what the internally-threaded context built up along the way.
    assert list(result.step_results) == ["first", "second"]
    assert result.step_results["first"].payload == {"n": 1}
    assert result.step_results["second"].payload == {"n": 2}


def test_workflow_publishes_started_then_completed_on_success() -> None:
    event_bus = _RecordingEventBus()
    engine = WorkflowEngine(_make_execution_engine(), event_bus=event_bus)
    definition = WorkflowDefinition(name="greet", steps=(_step("only"),))
    workflow = Workflow(definition=definition)

    engine.run(workflow, _make_context())

    assert [type(event) for event in event_bus.published] == [WorkflowStarted, WorkflowCompleted]
    started, completed = event_bus.published
    assert isinstance(started, WorkflowStarted)
    assert isinstance(completed, WorkflowCompleted)
    assert started.workflow_id == workflow.workflow_id == completed.workflow_id
    assert completed.step_count == 1


def test_workflow_publishes_started_then_failed_on_stopping_failure() -> None:
    event_bus = _RecordingEventBus()
    engine = WorkflowEngine(_make_execution_engine(with_failing_tool=True), event_bus=event_bus)
    definition = WorkflowDefinition(name="failing", steps=(_step("bad", operation="always-fails"),))
    workflow = Workflow(definition=definition)

    engine.run(workflow, _make_context())

    assert [type(event) for event in event_bus.published] == [WorkflowStarted, WorkflowFailed]
    failed = event_bus.published[1]
    assert isinstance(failed, WorkflowFailed)
    assert failed.stopped_at == "bad"


def test_workflow_without_event_bus_publishes_nothing() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="greet", steps=(_step("only"),))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True  # no event bus wired in, nothing to assert on it


def test_workflow_records_a_successful_run_to_memory() -> None:
    memory = InMemoryStore()
    engine = WorkflowEngine(_make_execution_engine(), memory=memory)
    definition = WorkflowDefinition(name="greet", steps=(_step("only"),))
    workflow = Workflow(definition=definition)

    engine.run(workflow, _make_context())

    entry = memory.get(workflow.workflow_id)
    assert entry is not None
    assert entry.tags == frozenset({"workflow"})
    assert entry.metadata == {"name": "greet", "success": True, "step_count": 1}


def test_workflow_records_a_failed_run_to_memory() -> None:
    memory = InMemoryStore()
    engine = WorkflowEngine(_make_execution_engine(with_failing_tool=True), memory=memory)
    definition = WorkflowDefinition(name="failing", steps=(_step("bad", operation="always-fails"),))
    workflow = Workflow(definition=definition)

    engine.run(workflow, _make_context())

    entry = memory.get(workflow.workflow_id)
    assert entry is not None
    assert entry.metadata["success"] is False


def test_workflow_without_memory_configured_records_nothing() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="greet", steps=(_step("only"),))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True  # no memory wired in, nothing to assert on it
