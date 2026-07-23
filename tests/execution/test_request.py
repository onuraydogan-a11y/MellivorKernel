"""Tests for mellivor_kernel.execution.request."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget, ExecutionValidationError


def test_request_defaults() -> None:
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    assert request.target == ExecutionTarget.TOOL
    assert request.operation == "echo"
    assert dict(request.payload) == {}
    assert request.request_id != ""


def test_request_auto_generates_unique_ids() -> None:
    first = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")
    second = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    assert first.request_id != second.request_id


def test_request_accepts_explicit_id_and_payload() -> None:
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="fake",
        payload={"prompt": "hello"},
        request_id="fixed-id",
    )

    assert request.request_id == "fixed-id"
    assert request.payload == {"prompt": "hello"}


def test_blank_operation_rejected() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="   ")


def test_blank_request_id_rejected() -> None:
    with pytest.raises(ExecutionValidationError):
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", request_id="  ")


def test_request_is_immutable() -> None:
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.operation = "other"  # type: ignore[misc]
