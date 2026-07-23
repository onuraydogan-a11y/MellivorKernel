"""Tests for mellivor_kernel.workflow.events."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.events import Event
from mellivor_kernel.workflow import WorkflowCompleted, WorkflowFailed, WorkflowStarted


def test_workflow_started_carries_identifying_fields() -> None:
    event = WorkflowStarted(workflow_id="abc", name="greet")

    assert isinstance(event, Event)
    assert event.workflow_id == "abc"
    assert event.name == "greet"
    assert event.event_id


def test_workflow_completed_carries_step_count() -> None:
    event = WorkflowCompleted(workflow_id="abc", name="greet", step_count=3)

    assert event.step_count == 3


def test_workflow_failed_defaults_stopped_at_to_none() -> None:
    event = WorkflowFailed(workflow_id="abc", name="greet", error="boom")

    assert event.error == "boom"
    assert event.stopped_at is None


def test_workflow_failed_can_carry_stopped_at() -> None:
    event = WorkflowFailed(workflow_id="abc", name="greet", error="boom", stopped_at="step-1")

    assert event.stopped_at == "step-1"


def test_workflow_events_are_immutable() -> None:
    event = WorkflowStarted(workflow_id="abc", name="greet")

    with pytest.raises(dataclasses.FrozenInstanceError):
        event.name = "other"  # type: ignore[misc]
