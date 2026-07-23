"""Public API of the kernel's execution core subsystem.

The execution core orchestrates execution only: it validates and dispatches
an :class:`ExecutionRequest` to the proper subsystem and returns a common
:class:`ExecutionResult`. It is deliberately provider-agnostic, tool-
agnostic, and free of business logic -- authorization, workflow, memory,
and agent concerns all belong to other, future subsystems.
"""

from __future__ import annotations

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.dispatch import Dispatcher
from mellivor_kernel.execution.engine import ExecutionEngine
from mellivor_kernel.execution.exceptions import (
    DispatchError,
    ExecutionError,
    ExecutionValidationError,
)
from mellivor_kernel.execution.request import ExecutionRequest, ExecutionTarget
from mellivor_kernel.execution.result import ExecutionResult

__all__ = [
    "DispatchError",
    "Dispatcher",
    "ExecutionContext",
    "ExecutionEngine",
    "ExecutionError",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionTarget",
    "ExecutionValidationError",
]
