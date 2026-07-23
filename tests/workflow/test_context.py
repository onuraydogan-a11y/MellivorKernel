"""Tests for mellivor_kernel.workflow.context."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import ExecutionContext, ExecutionResult
from mellivor_kernel.workflow import WorkflowContext


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _execution_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_workflow_context"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_context_defaults_to_no_step_results() -> None:
    execution_context = _execution_context()
    context = WorkflowContext(execution_context=execution_context)

    assert context.execution_context is execution_context
    assert dict(context.step_results) == {}


def test_context_holds_step_results() -> None:
    result = ExecutionResult(success=True, payload={"x": 1})
    context = WorkflowContext(execution_context=_execution_context(), step_results={"a": result})

    assert context.step_results["a"] is result


def test_context_is_immutable() -> None:
    context = WorkflowContext(execution_context=_execution_context())

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.step_results = {}  # type: ignore[misc]
