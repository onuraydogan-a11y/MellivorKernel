"""Execution lifecycle events, published by ExecutionEngine.

These are ``execution``'s own event types, not part of the generic
``events`` subsystem -- ``events`` stays free of any knowledge of
"execution" as a concept, per ADR-0008.
"""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.events import Event
from mellivor_kernel.execution.request import ExecutionTarget


@dataclass(frozen=True, slots=True)
class ExecutionStarted(Event):
    """Published once, at the start of :meth:`ExecutionEngine.execute`.

    Attributes:
        request_id: The executed request's own id, for correlation with
            the eventual :class:`ExecutionCompleted`/:class:`ExecutionFailed`.
        target: Which subsystem the request was dispatched to.
        operation: The tool id or provider name being executed.
    """

    request_id: str
    target: ExecutionTarget
    operation: str


@dataclass(frozen=True, slots=True)
class ExecutionCompleted(Event):
    """Published when an execution's result is successful.

    Attributes:
        request_id: The executed request's own id.
        target: Which subsystem the request was dispatched to.
        operation: The tool id or provider name that was executed.
        execution_time_seconds: Wall-clock time reported by the result.
    """

    request_id: str
    target: ExecutionTarget
    operation: str
    execution_time_seconds: float


@dataclass(frozen=True, slots=True)
class ExecutionFailed(Event):
    """Published when an execution's result is unsuccessful.

    Fires regardless of *why* the execution failed -- an authorization
    denial, a dispatch failure, or an exception during a tool or provider
    call are all represented uniformly here; the failure's own detail is
    always available in ``error``/``stage``.

    Attributes:
        request_id: The executed request's own id.
        target: Which subsystem the request was dispatched to.
        operation: The tool id or provider name that was attempted.
        error: The failure's human-readable description.
        stage: The stage the failure occurred at (for example
            ``"authorization"`` or ``"permission_check"``), if the
            underlying result recorded one.
    """

    request_id: str
    target: ExecutionTarget
    operation: str
    error: str
    stage: str | None = None
