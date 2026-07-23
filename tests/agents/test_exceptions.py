"""Tests for mellivor_kernel.agents.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.agents import AgentError
from mellivor_kernel.core import KernelError


def test_agent_error_derives_from_kernel_error() -> None:
    assert issubclass(AgentError, KernelError)


def test_agent_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise AgentError("boom")
