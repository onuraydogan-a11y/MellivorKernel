"""Tests for mellivor_kernel.workflow.step."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.workflow import WorkflowError, WorkflowStep


def _request() -> ExecutionRequest:
    return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")


def test_step_defaults() -> None:
    request = _request()
    step = WorkflowStep(name="greet", request=request)

    assert step.name == "greet"
    assert step.request is request
    assert step.granted_permissions == frozenset()
    assert step.continue_on_failure is False


def test_step_accepts_permissions_and_continue_on_failure() -> None:
    step = WorkflowStep(
        name="greet",
        request=_request(),
        granted_permissions=frozenset({"kernel.internal"}),
        continue_on_failure=True,
    )

    assert step.granted_permissions == frozenset({"kernel.internal"})
    assert step.continue_on_failure is True


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_name_rejected(blank: str) -> None:
    with pytest.raises(WorkflowError):
        WorkflowStep(name=blank, request=_request())


def test_step_is_immutable() -> None:
    step = WorkflowStep(name="greet", request=_request())

    with pytest.raises(dataclasses.FrozenInstanceError):
        step.name = "other"  # type: ignore[misc]
