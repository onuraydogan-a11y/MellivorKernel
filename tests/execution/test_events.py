"""Tests for mellivor_kernel.execution.events."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.events import Event
from mellivor_kernel.execution import (
    ExecutionCompleted,
    ExecutionFailed,
    ExecutionStarted,
    ExecutionTarget,
)


def test_execution_started_carries_identifying_fields() -> None:
    event = ExecutionStarted(request_id="abc", target=ExecutionTarget.TOOL, operation="echo")

    assert isinstance(event, Event)
    assert event.request_id == "abc"
    assert event.target == ExecutionTarget.TOOL
    assert event.operation == "echo"
    assert event.event_id


def test_execution_completed_carries_timing() -> None:
    event = ExecutionCompleted(
        request_id="abc",
        target=ExecutionTarget.TOOL,
        operation="echo",
        execution_time_seconds=0.5,
    )

    assert event.execution_time_seconds == 0.5


def test_execution_failed_defaults_stage_to_none() -> None:
    event = ExecutionFailed(
        request_id="abc", target=ExecutionTarget.TOOL, operation="echo", error="boom"
    )

    assert event.error == "boom"
    assert event.stage is None


def test_execution_failed_can_carry_a_stage() -> None:
    event = ExecutionFailed(
        request_id="abc",
        target=ExecutionTarget.TOOL,
        operation="echo",
        error="boom",
        stage="permission_check",
    )

    assert event.stage == "permission_check"


def test_execution_events_are_immutable() -> None:
    event = ExecutionStarted(request_id="abc", target=ExecutionTarget.TOOL, operation="echo")

    with pytest.raises(dataclasses.FrozenInstanceError):
        event.operation = "other"  # type: ignore[misc]
