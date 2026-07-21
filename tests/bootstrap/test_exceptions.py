"""Tests for mellivor_kernel.bootstrap.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.bootstrap import BootstrapError
from mellivor_kernel.core import KernelError


def test_bootstrap_error_derives_from_kernel_error() -> None:
    assert issubclass(BootstrapError, KernelError)


def test_bootstrap_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise BootstrapError("boom")
