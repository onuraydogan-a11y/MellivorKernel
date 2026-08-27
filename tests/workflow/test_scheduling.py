"""Tests for non-blocking workflow scheduling guards (ADR-0024, Part C)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

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
from mellivor_kernel.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowError,
    WorkflowExecutionOptions,
    WorkflowResult,
    WorkflowStep,
)


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


@dataclass
class _FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


class _CountingExecutionEngine(ExecutionEngine):
    def __init__(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        super().__init__(Dispatcher(registry, ProviderRegistry()))
        self.calls = 0

    def execute(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult:
        self.calls += 1
        return super().execute(request, context, granted_permissions=granted_permissions)


def _context() -> WorkflowContext:
    settings = _FakeSettings()
    return WorkflowContext(
        execution_context=ExecutionContext(
            configuration=settings,
            logger=get_logger("test_scheduling"),
            runtime=Kernel(settings),
            services=ServiceContainer(),
        )
    )


def _step() -> WorkflowStep:
    return WorkflowStep(
        name="scheduled",
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={"executed": True},
        ),
    )


def _run(
    engine: WorkflowEngine, step: WorkflowStep, *, not_before: datetime | None = None
) -> WorkflowResult:
    options = (
        WorkflowExecutionOptions(not_before={step.name: not_before})
        if not_before is not None
        else None
    )
    return engine.run(
        Workflow(definition=WorkflowDefinition(name="schedule", steps=(step,))),
        _context(),
        options=options,
    )


def test_step_without_schedule_executes_immediately() -> None:
    execution_engine = _CountingExecutionEngine()

    result = _run(WorkflowEngine(execution_engine), _step())

    assert result.success is True
    assert execution_engine.calls == 1


def test_future_step_fails_without_sleeping_or_invoking_execution() -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC)
    execution_engine = _CountingExecutionEngine()

    result = _run(
        WorkflowEngine(execution_engine, clock=_FakeClock(now)),
        _step(),
        not_before=now + timedelta(seconds=1),
    )

    assert result.success is False
    assert result.stopped_at == "scheduled"
    assert result.step_results["scheduled"].metadata["stage"] == "scheduling"
    assert execution_engine.calls == 0


def test_step_executes_when_injected_clock_reaches_not_before() -> None:
    due = datetime(2030, 1, 1, tzinfo=UTC)
    execution_engine = _CountingExecutionEngine()

    result = _run(WorkflowEngine(execution_engine, clock=_FakeClock(due)), _step(), not_before=due)

    assert result.success is True
    assert execution_engine.calls == 1


def test_past_schedule_executes_immediately() -> None:
    now = datetime(2030, 1, 2, tzinfo=UTC)
    execution_engine = _CountingExecutionEngine()

    result = _run(
        WorkflowEngine(execution_engine, clock=_FakeClock(now)),
        _step(),
        not_before=now - timedelta(days=1),
    )

    assert result.success is True
    assert execution_engine.calls == 1


def test_naive_not_before_is_rejected() -> None:
    with pytest.raises(WorkflowError, match="timezone-aware"):
        WorkflowExecutionOptions(not_before={"scheduled": datetime(2030, 1, 1)})


def test_advancing_fake_clock_makes_a_new_run_eligible_without_background_work() -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC)
    clock = _FakeClock(now)
    execution_engine = _CountingExecutionEngine()
    workflow_engine = WorkflowEngine(execution_engine, clock=clock)
    step = _step()
    scheduled_at = now + timedelta(minutes=1)

    first = _run(workflow_engine, step, not_before=scheduled_at)
    clock.current += timedelta(minutes=1)
    second = _run(workflow_engine, step, not_before=scheduled_at)

    assert first.success is False
    assert second.success is True
    assert execution_engine.calls == 1
