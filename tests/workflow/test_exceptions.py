"""Tests for mellivor_kernel.workflow.exceptions."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import KernelError
from mellivor_kernel.workflow import WorkflowError


def test_workflow_error_derives_from_kernel_error() -> None:
    assert issubclass(WorkflowError, KernelError)


def test_workflow_error_is_catchable_as_kernel_error() -> None:
    with pytest.raises(KernelError):
        raise WorkflowError("boom")
