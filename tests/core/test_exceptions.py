"""Tests for mellivor_kernel.core.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import (
    ConfigurationError,
    KernelError,
    ServiceRegistrationError,
    StartupError,
)


@pytest.mark.parametrize(
    "exception_type",
    [ConfigurationError, ServiceRegistrationError, StartupError],
)
def test_kernel_exceptions_derive_from_kernel_error(exception_type: type[KernelError]) -> None:
    assert issubclass(exception_type, KernelError)


def test_kernel_error_derives_from_exception() -> None:
    assert issubclass(KernelError, Exception)


def test_kernel_error_carries_message() -> None:
    error = KernelError("something went wrong")

    assert str(error) == "something went wrong"


def test_subclasses_are_raisable_and_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise StartupError("boom")
