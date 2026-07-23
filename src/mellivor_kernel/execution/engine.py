"""ExecutionEngine: the kernel's single execution orchestration entry point."""

from __future__ import annotations

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.contracts import Authorizer
from mellivor_kernel.execution.dispatch import Dispatcher
from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.execution.result import ExecutionResult


class ExecutionEngine:
    """The kernel's single orchestration entry point for execution.

    Responsible only for validation, authorization gating, dispatch
    selection, and the execution lifecycle (start/outcome logging) of a
    request. Request validation is enforced by
    :class:`~mellivor_kernel.execution.request.ExecutionRequest` itself at
    construction -- an immutable request cannot exist in an invalid state,
    so the engine has nothing further to validate before handing it to the
    :class:`Dispatcher`.

    The flow is ``ExecutionRequest -> Authorization -> Dispatcher ->
    Tool/Provider -> ExecutionResult``: when an :class:`Authorizer` is
    configured, it is consulted *before* dispatch, and a denial short-
    circuits the request into a failed :class:`ExecutionResult` without
    ever reaching the :class:`Dispatcher`. The engine only ever consumes
    the authorizer's :class:`~mellivor_kernel.execution.contracts.AuthorizationOutcome`
    -- it has no knowledge of how that decision is reached (see
    :mod:`mellivor_kernel.execution.contracts`).

    Deliberately excludes retry logic and workflow composition -- neither
    is an execution-orchestration concern.
    """

    def __init__(self, dispatcher: Dispatcher, *, authorizer: Authorizer | None = None) -> None:
        """Initialize the engine.

        Args:
            dispatcher: The dispatcher used to route requests to their
                target subsystem.
            authorizer: The authorizer consulted before dispatch. If
                ``None`` (the default), no authorization check is
                performed and no permissions are ever forwarded to the
                dispatcher -- identical to this engine's behavior before
                authorization existed.
        """
        self._dispatcher = dispatcher
        self._authorizer = authorizer

    def execute(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult:
        """Run ``request`` through the execution lifecycle.

        Args:
            request: The request to execute.
            context: The execution-lifetime context to execute with.
            granted_permissions: The permission identifiers (as raw
                strings) the caller claims to hold for this request.
                Ignored unless an :attr:`authorizer` is configured -- with
                no authorizer, no permissions are ever forwarded to the
                dispatcher, matching this engine's pre-authorization
                behavior exactly.

        Returns:
            A failed :class:`ExecutionResult` if an authorizer is
            configured and denies the request (``metadata["stage"] ==
            "authorization"``), without ever reaching the
            :class:`Dispatcher`. Otherwise, the outcome produced by the
            :class:`Dispatcher`.
        """
        context.logger.info(
            "Executing request %r (target=%s, operation=%r).",
            request.request_id,
            request.target.value,
            request.operation,
        )

        effective_permissions: frozenset[str] = frozenset()
        if self._authorizer is not None:
            outcome = self._authorizer.check(
                request, context, granted_permissions=granted_permissions
            )
            if not outcome.granted:
                result = ExecutionResult(
                    success=False,
                    error=outcome.reason or "Authorization denied.",
                    metadata={"stage": "authorization", "target": request.target.value},
                )
                context.logger.warning(
                    "Request %r denied by authorization: %s", request.request_id, result.error
                )
                return result
            effective_permissions = granted_permissions

        result = self._dispatcher.dispatch(
            request, context, granted_permissions=effective_permissions
        )

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
