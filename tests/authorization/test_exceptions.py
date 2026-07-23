"""Tests for mellivor_kernel.authorization.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.authorization import AuthorizationError
from mellivor_kernel.core import KernelError


def test_authorization_error_derives_from_kernel_error() -> None:
    assert issubclass(AuthorizationError, KernelError)


def test_authorization_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise AuthorizationError("boom")
