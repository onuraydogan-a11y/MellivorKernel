"""Public API of the kernel's execution core subsystem.

The execution core orchestrates execution only: it validates, authorizes,
dispatches, and publishes lifecycle events for an :class:`ExecutionRequest`,
returning a common :class:`ExecutionResult`. It is deliberately provider-
agnostic, tool-agnostic, and free of business logic. Authorization is
consulted through the small :class:`Authorizer`/:class:`AuthorizationOutcome`
contracts below -- execution never depends on, or knows how, an
authorization decision is reached; see
:mod:`mellivor_kernel.authorization` for the subsystem that decides it, and
ADR-0007 for why the two are decoupled this way. Lifecycle events are
published through :class:`~mellivor_kernel.events.bus.EventBus` -- an
abstract contract, never a concrete bus implementation; see
:mod:`mellivor_kernel.events` and ADR-0008. Workflow, memory, and agent
concerns remain other, future subsystems.
"""

from __future__ import annotations

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.contracts import AuthorizationOutcome, Authorizer
from mellivor_kernel.execution.dispatch import Dispatcher
from mellivor_kernel.execution.engine import ExecutionEngine
from mellivor_kernel.execution.events import ExecutionCompleted, ExecutionFailed, ExecutionStarted
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
    "ExecutionCompleted",
    "ExecutionContext",
    "ExecutionEngine",
    "ExecutionError",
    "ExecutionFailed",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStarted",
    "ExecutionTarget",
    "ExecutionValidationError",
]
