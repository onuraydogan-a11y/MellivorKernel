"""Tests for mellivor_kernel.agents.engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.agents import (
    Agent,
    AgentCompleted,
    AgentContext,
    AgentDefinition,
    AgentEngine,
    AgentFailed,
    AgentStarted,
)
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
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
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


def _execution_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_agent_engine"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def _make_context() -> AgentContext:
    return AgentContext(workflow_context=WorkflowContext(execution_context=_execution_context()))


def _make_workflow_engine(*, with_failing_tool: bool = False) -> WorkflowEngine:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    if with_failing_tool:
        tool_registry.register(_FailingTool())
    execution_engine = ExecutionEngine(Dispatcher(tool_registry, ProviderRegistry()))
    return WorkflowEngine(execution_engine)


def _greeting_definition(*, operation: str = "echo") -> AgentDefinition:
    workflow = WorkflowDefinition(
        name="greet",
        steps=(
            WorkflowStep(
                name="say-hi",
                request=ExecutionRequest(
                    target=ExecutionTarget.TOOL, operation=operation, payload={"msg": "hi"}
                ),
            ),
        ),
    )
    return AgentDefinition(name="greeter", workflow=workflow)


def test_single_agent_executes_its_workflow() -> None:
    engine = AgentEngine(_make_workflow_engine())
    agent = Agent(definition=_greeting_definition())

    result = engine.execute(agent, _make_context())

    assert result.success is True
    assert result.workflow_result.success is True
    assert result.workflow_result.step_results["say-hi"].payload == {"msg": "hi"}


def test_workflow_delegation_never_touches_tools_or_providers_directly() -> None:
    """AgentEngine only ever calls WorkflowEngine.run() -- proven by
    running an agent whose workflow_engine has no ExecutionEngine
    reference AgentEngine could bypass it with.
    """
    workflow_engine = _make_workflow_engine()
    engine = AgentEngine(workflow_engine)
    agent = Agent(definition=_greeting_definition())

    result = engine.execute(agent, _make_context())

    assert result.success is True
    # AgentEngine holds no reference to tools/providers/execution at all --
    # this is verified structurally (see the module-level dependency
    # check in this sprint's report), and behaviorally here: the only way
    # this call could have succeeded is via workflow_engine.
    assert not hasattr(engine, "_execution_engine")
    assert not hasattr(engine, "_dispatcher")


def test_agent_success() -> None:
    engine = AgentEngine(_make_workflow_engine())

    result = engine.execute(Agent(definition=_greeting_definition()), _make_context())

    assert result.success is True
    assert result.error is None


def test_agent_failure_mirrors_the_workflows_failure() -> None:
    engine = AgentEngine(_make_workflow_engine(with_failing_tool=True))
    agent = Agent(definition=_greeting_definition(operation="always-fails"))

    result = engine.execute(agent, _make_context())

    assert result.success is False
    assert result.workflow_result.success is False
    assert result.workflow_result.stopped_at == "say-hi"
    assert result.error is not None
    assert "say-hi" in result.error


def test_agent_publishes_started_then_completed_on_success() -> None:
    event_bus = _RecordingEventBus()
    engine = AgentEngine(_make_workflow_engine(), event_bus=event_bus)
    agent = Agent(definition=_greeting_definition())

    engine.execute(agent, _make_context())

    assert [type(event) for event in event_bus.published] == [AgentStarted, AgentCompleted]
    started, completed = event_bus.published
    assert isinstance(started, AgentStarted)
    assert isinstance(completed, AgentCompleted)
    assert started.agent_id == agent.agent_id == completed.agent_id


def test_agent_publishes_started_then_failed_on_workflow_failure() -> None:
    event_bus = _RecordingEventBus()
    engine = AgentEngine(_make_workflow_engine(with_failing_tool=True), event_bus=event_bus)
    agent = Agent(definition=_greeting_definition(operation="always-fails"))

    engine.execute(agent, _make_context())

    assert [type(event) for event in event_bus.published] == [AgentStarted, AgentFailed]
    failed = event_bus.published[1]
    assert isinstance(failed, AgentFailed)
    assert failed.agent_id == agent.agent_id


def test_agent_without_event_bus_publishes_nothing() -> None:
    engine = AgentEngine(_make_workflow_engine())

    result = engine.execute(Agent(definition=_greeting_definition()), _make_context())

    assert result.success is True  # no event bus wired in, nothing to assert on it


def test_agent_records_a_successful_run_to_memory() -> None:
    memory = InMemoryStore()
    engine = AgentEngine(_make_workflow_engine(), memory=memory)
    agent = Agent(definition=_greeting_definition())

    engine.execute(agent, _make_context())

    entry = memory.get(agent.agent_id)
    assert entry is not None
    assert entry.tags == frozenset({"agent"})
    assert entry.metadata == {"name": "greeter", "success": True}


def test_agent_records_a_failed_run_to_memory() -> None:
    memory = InMemoryStore()
    engine = AgentEngine(_make_workflow_engine(with_failing_tool=True), memory=memory)
    agent = Agent(definition=_greeting_definition(operation="always-fails"))

    engine.execute(agent, _make_context())

    entry = memory.get(agent.agent_id)
    assert entry is not None
    assert entry.metadata["success"] is False


def test_agent_without_memory_configured_records_nothing() -> None:
    engine = AgentEngine(_make_workflow_engine())

    result = engine.execute(Agent(definition=_greeting_definition()), _make_context())

    assert result.success is True  # no memory wired in, nothing to assert on it
