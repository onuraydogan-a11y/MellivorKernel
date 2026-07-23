"""ExecutionEngine: the kernel's single execution orchestration entry point."""

from __future__ import annotations

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.dispatch import Dispatcher
from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.execution.result import ExecutionResult


class ExecutionEngine:
    """The kernel's single orchestration entry point for execution.

    Responsible only for validation, dispatch selection, and the execution
    lifecycle (start/outcome logging) of a request. Request validation is
    enforced by :class:`~mellivor_kernel.execution.request.ExecutionRequest`
    itself at construction -- an immutable request cannot exist in an
    invalid state, so the engine has nothing further to validate before
    handing it to the :class:`Dispatcher`.

    Deliberately excludes authorization (a future subsystem), retry logic,
    and workflow composition -- none of which are execution-orchestration
    concerns.
    """

    def __init__(self, dispatcher: Dispatcher) -> None:
        """Initialize the engine.

        Args:
            dispatcher: The dispatcher used to route requests to their
                target subsystem.
        """
        self._dispatcher = dispatcher

    def execute(self, request: ExecutionRequest, context: ExecutionContext) -> ExecutionResult:
        """Run ``request`` through the execution lifecycle.

        Args:
            request: The request to execute.
            context: The execution-lifetime context to execute with.

        Returns:
            The outcome of the execution, as produced by the
            :class:`Dispatcher`.
        """
        context.logger.info(
            "Executing request %r (target=%s, operation=%r).",
            request.request_id,
            request.target.value,
            request.operation,
        )

        result = self._dispatcher.dispatch(request, context)

        if result.success:
            context.logger.info(
                "Request %r succeeded in %.6fs.",
                request.request_id,
                result.execution_time_seconds,
            )
        else:
            context.logger.warning(
                "Request %r failed: %s",
                request.request_id,
                result.error,
            )

        return result
