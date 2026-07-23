"""Tests for mellivor_kernel.authorization.permission_set."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.authorization import PermissionSet
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL, NETWORK_READ


def test_empty_permission_set() -> None:
    permission_set = PermissionSet.empty()

    assert permission_set.permissions == frozenset()


def test_permission_set_holds_given_permissions() -> None:
    permission_set = PermissionSet(frozenset({KERNEL_INTERNAL, NETWORK_READ}))

    assert permission_set.permissions == frozenset({KERNEL_INTERNAL, NETWORK_READ})


def test_permission_set_is_immutable() -> None:
    permission_set = PermissionSet.empty()

    with pytest.raises(dataclasses.FrozenInstanceError):
        permission_set.permissions = frozenset({KERNEL_INTERNAL})  # type: ignore[misc]
