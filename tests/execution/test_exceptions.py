"""Tests for mellivor_kernel.execution.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.execution import DispatchError, ExecutionError, ExecutionValidationError


@pytest.mark.parametrize("exception_type", [DispatchError, ExecutionValidationError])
def test_execution_exceptions_derive_from_execution_error(
    exception_type: type[ExecutionError],
) -> None:
    assert issubclass(exception_type, ExecutionError)


def test_execution_error_derives_from_kernel_error() -> None:
    assert issubclass(ExecutionError, KernelError)


def test_execution_exceptions_are_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise ExecutionValidationError("boom")
