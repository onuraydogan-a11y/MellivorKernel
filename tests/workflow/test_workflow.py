"""Tests for mellivor_kernel.workflow.workflow."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.workflow import Workflow, WorkflowDefinition


def test_workflow_auto_generates_id() -> None:
    definition = WorkflowDefinition(name="greet")
    workflow = Workflow(definition=definition)

    assert isinstance(workflow.workflow_id, str) and workflow.workflow_id
    assert workflow.definition is definition


def test_workflow_ids_are_unique() -> None:
    definition = WorkflowDefinition(name="greet")

    first = Workflow(definition=definition)
    second = Workflow(definition=definition)

    assert first.workflow_id != second.workflow_id


def test_workflow_accepts_explicit_id() -> None:
    workflow = Workflow(definition=WorkflowDefinition(name="greet"), workflow_id="fixed-id")

    assert workflow.workflow_id == "fixed-id"


def test_workflow_is_immutable() -> None:
    workflow = Workflow(definition=WorkflowDefinition(name="greet"))

    with pytest.raises(dataclasses.FrozenInstanceError):
        workflow.workflow_id = "other"  # type: ignore[misc]
