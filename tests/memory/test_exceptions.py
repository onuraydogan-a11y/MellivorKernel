"""Tests for mellivor_kernel.memory.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.memory import MemoryError


def test_memory_error_derives_from_kernel_error() -> None:
    assert issubclass(MemoryError, KernelError)


def test_memory_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise MemoryError("boom")
