"""Tests for mellivor_kernel.agents.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.agents import AgentError, AgentResult
from mellivor_kernel.workflow import WorkflowResult


def test_successful_result_defaults() -> None:
    workflow_result = WorkflowResult(success=True)
    result = AgentResult(success=True, workflow_result=workflow_result)

    assert result.success is True
    assert result.workflow_result is workflow_result
    assert result.error is None


def test_failed_result_requires_error_message() -> None:
    with pytest.raises(AgentError):
        AgentResult(success=False, workflow_result=WorkflowResult(success=True))


def test_failed_result_rejects_blank_error_message() -> None:
    with pytest.raises(AgentError):
        AgentResult(success=False, workflow_result=WorkflowResult(success=True), error="   ")


def test_successful_result_rejects_error_message() -> None:
    with pytest.raises(AgentError):
        AgentResult(
            success=True, workflow_result=WorkflowResult(success=True), error="should not be set"
        )


def test_failed_result_with_error() -> None:
    workflow_result = WorkflowResult(success=False, error="boom", stopped_at="step-1")
    result = AgentResult(success=False, workflow_result=workflow_result, error="workflow failed")

    assert result.error == "workflow failed"
    assert result.workflow_result is workflow_result


def test_result_is_immutable() -> None:
    result = AgentResult(success=True, workflow_result=WorkflowResult(success=True))

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]
