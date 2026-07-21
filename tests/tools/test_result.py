"""Tests for mellivor_kernel.tools.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.tools import ToolResult, ToolValidationError


def test_successful_result_defaults() -> None:
    result = ToolResult(success=True, payload={"answer": 42})

    assert result.success is True
    assert result.payload == {"answer": 42}
    assert result.error is None
    assert result.execution_time_seconds == 0.0
    assert dict(result.metadata) == {}


def test_failed_result_requires_error_message() -> None:
    with pytest.raises(ToolValidationError):
        ToolResult(success=False)


def test_failed_result_rejects_blank_error_message() -> None:
    with pytest.raises(ToolValidationError):
        ToolResult(success=False, error="   ")


def test_successful_result_rejects_error_message() -> None:
    with pytest.raises(ToolValidationError):
        ToolResult(success=True, error="should not be set")


def test_rejects_negative_execution_time() -> None:
    with pytest.raises(ToolValidationError):
        ToolResult(success=True, execution_time_seconds=-1.0)


def test_result_is_immutable() -> None:
    result = ToolResult(success=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_failed_result_with_metadata() -> None:
    result = ToolResult(success=False, error="denied", metadata={"stage": "permission_check"})

    assert result.metadata["stage"] == "permission_check"
