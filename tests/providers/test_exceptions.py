"""Tests for mellivor_kernel.providers.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.providers import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRegistrationError,
)


@pytest.mark.parametrize("exception_type", [ProviderConfigurationError, ProviderRegistrationError])
def test_provider_exceptions_derive_from_provider_error(
    exception_type: type[ProviderError],
) -> None:
    assert issubclass(exception_type, ProviderError)


def test_provider_error_derives_from_kernel_error() -> None:
    assert issubclass(ProviderError, KernelError)


def test_provider_exceptions_are_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise ProviderConfigurationError("boom")
