"""Tests for mellivor_kernel.workflow.definition."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.workflow import WorkflowDefinition, WorkflowError, WorkflowStep


def _step(name: str) -> WorkflowStep:
    return WorkflowStep(
        name=name, request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")
    )


def test_definition_defaults_to_no_steps() -> None:
    definition = WorkflowDefinition(name="empty")

    assert definition.steps == ()
    assert dict(definition.metadata) == {}


def test_definition_accepts_steps_and_metadata() -> None:
    definition = WorkflowDefinition(
        name="greet", steps=(_step("a"), _step("b")), metadata={"owner": "team-x"}
    )

    assert [step.name for step in definition.steps] == ["a", "b"]
    assert definition.metadata == {"owner": "team-x"}


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_name_rejected(blank: str) -> None:
    with pytest.raises(WorkflowError):
        WorkflowDefinition(name=blank)


def test_duplicate_step_names_rejected() -> None:
    with pytest.raises(WorkflowError):
        WorkflowDefinition(name="greet", steps=(_step("a"), _step("a")))


def test_definition_is_immutable() -> None:
    definition = WorkflowDefinition(name="greet")

    with pytest.raises(dataclasses.FrozenInstanceError):
        definition.name = "other"  # type: ignore[misc]
