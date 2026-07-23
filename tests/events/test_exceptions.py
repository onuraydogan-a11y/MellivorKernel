"""Tests for mellivor_kernel.events.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.events import EventDispatchError


def test_event_dispatch_error_derives_from_kernel_error() -> None:
    assert issubclass(EventDispatchError, KernelError)


def test_event_dispatch_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise EventDispatchError("boom")
