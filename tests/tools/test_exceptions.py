"""Tests for mellivor_kernel.tools.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.tools import ToolError, ToolRegistrationError, ToolValidationError


@pytest.mark.parametrize("exception_type", [ToolRegistrationError, ToolValidationError])
def test_tool_exceptions_derive_from_tool_error(exception_type: type[ToolError]) -> None:
    assert issubclass(exception_type, ToolError)


def test_tool_error_derives_from_kernel_error() -> None:
    assert issubclass(ToolError, KernelError)


def test_tool_exceptions_are_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise ToolValidationError("boom")
