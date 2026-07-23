"""Tests for mellivor_kernel.execution.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.execution import ExecutionResult, ExecutionValidationError


def test_successful_result_defaults() -> None:
    result = ExecutionResult(success=True, payload={"answer": 42})

    assert result.success is True
    assert result.payload == {"answer": 42}
    assert result.error is None
    assert result.execution_time_seconds == 0.0
    assert dict(result.metadata) == {}


def test_failed_result_requires_error_message() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionResult(success=False)


def test_failed_result_rejects_blank_error_message() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionResult(success=False, error="   ")


def test_successful_result_rejects_error_message() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionResult(success=True, error="should not be set")


def test_rejects_negative_execution_time() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionResult(success=True, execution_time_seconds=-1.0)


def test_result_is_immutable() -> None:
    result = ExecutionResult(success=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_failed_result_with_metadata() -> None:
    result = ExecutionResult(success=False, error="denied", metadata={"target": "tool"})

    assert result.metadata["target"] == "tool"
