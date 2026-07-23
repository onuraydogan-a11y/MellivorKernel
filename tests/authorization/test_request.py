"""Tests for mellivor_kernel.authorization.request."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.authorization import AuthorizationError, AuthorizationRequest, PermissionSet
from mellivor_kernel.execution import ExecutionTarget
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL


def test_request_defaults() -> None:
    request = AuthorizationRequest(target=ExecutionTarget.TOOL, operation="health_check")

    assert request.target == ExecutionTarget.TOOL
    assert request.operation == "health_check"
    assert request.granted_permissions == PermissionSet.empty()


def test_request_accepts_granted_permissions() -> None:
    request = AuthorizationRequest(
        target=ExecutionTarget.TOOL,
        operation="health_check",
        granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL})),
    )

    assert request.granted_permissions.permissions == frozenset({KERNEL_INTERNAL})


def test_blank_operation_rejected() -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationRequest(target=ExecutionTarget.TOOL, operation="   ")


def test_request_is_immutable() -> None:
    request = AuthorizationRequest(target=ExecutionTarget.TOOL, operation="health_check")

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.operation = "other"  # type: ignore[misc]
