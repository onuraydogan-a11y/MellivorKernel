"""Tests for mellivor_kernel.workflow.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.execution import ExecutionResult
from mellivor_kernel.workflow import WorkflowError, WorkflowResult


def test_successful_result_defaults() -> None:
    result = WorkflowResult(success=True)

    assert result.success is True
    assert dict(result.step_results) == {}
    assert result.error is None
    assert result.stopped_at is None


def test_successful_result_can_carry_step_results() -> None:
    step_result = ExecutionResult(success=True, payload={"x": 1})
    result = WorkflowResult(success=True, step_results={"a": step_result})

    assert result.step_results["a"] is step_result


def test_failed_result_requires_error_message() -> None:
    with pytest.raises(WorkflowError):
        WorkflowResult(success=False)


def test_failed_result_rejects_blank_error_message() -> None:
    with pytest.raises(WorkflowError):
        WorkflowResult(success=False, error="   ")


def test_successful_result_rejects_error_message() -> None:
    with pytest.raises(WorkflowError):
        WorkflowResult(success=True, error="should not be set")


def test_successful_result_rejects_stopped_at() -> None:
    with pytest.raises(WorkflowError):
        WorkflowResult(success=True, stopped_at="some-step")


def test_failed_result_with_stopped_at() -> None:
    result = WorkflowResult(success=False, error="boom", stopped_at="some-step")

    assert result.stopped_at == "some-step"


def test_result_is_immutable() -> None:
    result = WorkflowResult(success=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]
