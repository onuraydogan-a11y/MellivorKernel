"""Tests for mellivor_kernel.agents.context."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pytest

from mellivor_kernel.agents import AgentContext
from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import ExecutionContext
from mellivor_kernel.workflow import WorkflowContext


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _execution_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_agent_context"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_context_holds_the_workflow_context() -> None:
    workflow_context = WorkflowContext(execution_context=_execution_context())
    context = AgentContext(workflow_context=workflow_context)

    assert context.workflow_context is workflow_context


def test_context_is_immutable() -> None:
    context = AgentContext(workflow_context=WorkflowContext(execution_context=_execution_context()))

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.workflow_context = WorkflowContext(  # type: ignore[misc]
            execution_context=_execution_context()
        )
