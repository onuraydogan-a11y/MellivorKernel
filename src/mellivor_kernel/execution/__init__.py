"""Public API of the kernel's execution core subsystem.

The execution core orchestrates execution only: it validates, authorizes,
and dispatches an :class:`ExecutionRequest` to the proper subsystem and
returns a common :class:`ExecutionResult`. It is deliberately provider-
agnostic, tool-agnostic, and free of business logic. Authorization is
consulted through the small :class:`Authorizer`/:class:`AuthorizationOutcome`
contracts below -- execution never depends on, or knows how, an
authorization decision is reached; see
:mod:`mellivor_kernel.authorization` for the subsystem that decides it, and
ADR-0007 for why the two are decoupled this way. Workflow, memory, and
agent concerns remain other, future subsystems.
"""

from __future__ import annotations

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.contracts import AuthorizationOutcome, Authorizer
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
    "AuthorizationOutcome",
    "Authorizer",
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
