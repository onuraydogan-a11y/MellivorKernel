"""Tests for mellivor_kernel.authorization.result."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.authorization import AuthorizationError, AuthorizationResult, PermissionSet
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL


def test_granted_result_defaults() -> None:
    result = AuthorizationResult(granted=True)

    assert result.granted is True
    assert result.reason is None
    assert result.granted_permissions == PermissionSet.empty()


def test_granted_result_can_carry_permissions() -> None:
    result = AuthorizationResult(
        granted=True, granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL}))
    )

    assert result.granted_permissions.permissions == frozenset({KERNEL_INTERNAL})


def test_denied_result_requires_reason() -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationResult(granted=False)


def test_denied_result_rejects_blank_reason() -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationResult(granted=False, reason="   ")


def test_granted_result_rejects_reason() -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationResult(granted=True, reason="should not be set")


def test_denied_result_rejects_granted_permissions() -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationResult(
            granted=False,
            reason="denied",
            granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL})),
        )


def test_result_is_immutable() -> None:
    result = AuthorizationResult(granted=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.granted = False  # type: ignore[misc]
