"""Tests for mellivor_kernel.tools.permissions."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.tools import (
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    KERNEL_INTERNAL,
    NETWORK_READ,
    PROVIDER_INVOKE,
    Permission,
    ToolValidationError,
    missing_permissions,
)


def test_valid_permission_round_trips() -> None:
    permission = Permission("network.read")

    assert permission.value == "network.read"
    assert str(permission) == "network.read"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "nodots",
        "Has.Uppercase",
        "trailing.dot.",
        ".leadingdot",
        "double..dot",
        "spaces here.ok",
    ],
)
def test_rejects_malformed_permission(value: str) -> None:
    with pytest.raises(ToolValidationError):
        Permission(value)


def test_permission_is_immutable() -> None:
    permission = Permission("network.read")

    with pytest.raises(dataclasses.FrozenInstanceError):
        permission.value = "other.value"  # type: ignore[misc]


def test_well_known_permissions_are_valid() -> None:
    for permission in (
        NETWORK_READ,
        FILESYSTEM_READ,
        FILESYSTEM_WRITE,
        PROVIDER_INVOKE,
        KERNEL_INTERNAL,
    ):
        assert isinstance(permission, Permission)


def test_missing_permissions_returns_the_gap() -> None:
    required = frozenset({NETWORK_READ, FILESYSTEM_READ})
    granted = frozenset({NETWORK_READ})

    assert missing_permissions(required, granted) == frozenset({FILESYSTEM_READ})


def test_missing_permissions_empty_when_fully_granted() -> None:
    required = frozenset({NETWORK_READ})
    granted = frozenset({NETWORK_READ, FILESYSTEM_READ})

    assert missing_permissions(required, granted) == frozenset()


def test_business_specific_permission_strings_are_valid_but_not_predefined() -> None:
    # "crm.read" is a valid permission *format*; the kernel does not define
    # it as a constant, since CRM is a business domain (ADR-0003).
    permission = Permission("crm.read")

    assert permission.value == "crm.read"
