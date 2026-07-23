"""Execution Core exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class ExecutionError(KernelError):
    """Base class for all errors raised by the execution subsystem."""


class ExecutionValidationError(ExecutionError):
    """Raised when an ``ExecutionRequest`` or ``ExecutionResult`` is invalid."""


class DispatchError(ExecutionError):
    """Raised when a request cannot be dispatched to any execution target."""
