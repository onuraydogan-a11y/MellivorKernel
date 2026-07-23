"""ExecutionEngine: the kernel's single execution orchestration entry point."""

from __future__ import annotations

from mellivor_kernel.events import Event, EventBus
from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.contracts import Authorizer
from mellivor_kernel.execution.dispatch import Dispatcher
from mellivor_kernel.execution.events import ExecutionCompleted, ExecutionFailed, ExecutionStarted
from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.execution.result import ExecutionResult
from mellivor_kernel.memory import MemoryEntry, MemoryStore


class ExecutionEngine:
    """The kernel's single orchestration entry point for execution.

    Responsible only for validation, authorization gating, dispatch
    selection, event publication, memory recording, and the execution
    lifecycle (start/outcome logging) of a request. Request validation is
    enforced by :class:`~mellivor_kernel.execution.request.ExecutionRequest`
    itself at construction -- an immutable request cannot exist in an
    invalid state, so the engine has nothing further to validate before
    handing it to the :class:`Dispatcher`.

    The flow is ``ExecutionRequest -> Authorization -> Dispatcher ->
    Tool/Provider -> ExecutionResult``: when an :class:`Authorizer` is
    configured, it is consulted *before* dispatch, and a denial short-
    circuits the request into a failed :class:`ExecutionResult` without
    ever reaching the :class:`Dispatcher`. The engine only ever consumes
    the authorizer's :class:`~mellivor_kernel.execution.contracts.AuthorizationOutcome`
    -- it has no knowledge of how that decision is reached (see
    :mod:`mellivor_kernel.execution.contracts`).

    When an :class:`~mellivor_kernel.events.bus.EventBus` is configured,
    the engine publishes
    :class:`~mellivor_kernel.execution.events.ExecutionStarted`,
    :class:`~mellivor_kernel.execution.events.ExecutionCompleted`, and
    :class:`~mellivor_kernel.execution.events.ExecutionFailed` around the
    lifecycle above -- again through the abstract ``EventBus`` Protocol
    only, never a concrete bus implementation.

    When a :class:`~mellivor_kernel.memory.store.MemoryStore` is
    configured, the engine records every execution's outcome as a
    :class:`~mellivor_kernel.memory.entry.MemoryEntry` (keyed by
    ``request.request_id``) after the terminal event above is published --
    memory is kernel infrastructure the engine optionally *writes to*, not
    a provider concern; see ADR-0009. A failure to record memory is logged
    and never propagates -- a misbehaving memory backend must not break
    execution.

    Deliberately excludes retry logic and workflow composition -- neither
    is an execution-orchestration concern.
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        *,
        authorizer: Authorizer | None = None,
        event_bus: EventBus | None = None,
        memory: MemoryStore | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            dispatcher: The dispatcher used to route requests to their
                target subsystem.
            authorizer: The authorizer consulted before dispatch. If
                ``None`` (the default), no authorization check is
                performed and no permissions are ever forwarded to the
                dispatcher -- identical to this engine's behavior before
                authorization existed.
            event_bus: The bus lifecycle events are published to. If
                ``None`` (the default), no events are published --
                identical to this engine's behavior before the event bus
                existed.
            memory: The store execution outcomes are recorded to. If
                ``None`` (the default), nothing is recorded -- identical
                to this engine's behavior before memory existed.
        """
        self._dispatcher = dispatcher
        self._authorizer = authorizer
        self._event_bus = event_bus
        self._memory = memory

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
        self._publish(
            ExecutionStarted(
                request_id=request.request_id, target=request.target, operation=request.operation
            )
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
                return self._finish(request, result, context)
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

        return self._finish(request, result, context)

    def _finish(
        self, request: ExecutionRequest, result: ExecutionResult, context: ExecutionContext
    ) -> ExecutionResult:
        """Publish the terminal event, record memory, and return ``result`` unchanged."""
        if result.success:
            self._publish(
                ExecutionCompleted(
                    request_id=request.request_id,
                    target=request.target,
                    operation=request.operation,
                    execution_time_seconds=result.execution_time_seconds,
                )
            )
        else:
            stage = result.metadata.get("stage")
            self._publish(
                ExecutionFailed(
                    request_id=request.request_id,
                    target=request.target,
                    operation=request.operation,
                    error=result.error or "",
                    stage=stage if isinstance(stage, str) else None,
                )
            )
        self._remember(request, result, context)
        return result

    def _publish(self, event: Event) -> None:
        """Publish ``event`` if an :class:`~mellivor_kernel.events.bus.EventBus` is configured."""
        if self._event_bus is not None:
            self._event_bus.publish(event)

    def _remember(
        self, request: ExecutionRequest, result: ExecutionResult, context: ExecutionContext
    ) -> None:
        """Record ``result`` to memory if a
        :class:`~mellivor_kernel.memory.store.MemoryStore` is configured.

        Never raises: a memory backend failure is logged and swallowed
        rather than allowed to break execution.
        """
        if self._memory is None:
            return

        content = (
            str(result.payload) if result.success and result.payload is not None else result.error
        )
        entry = MemoryEntry(
            id=request.request_id,
            content=content or "(no content)",
            tags=frozenset({request.target.value}),
            metadata={"operation": request.operation, "success": result.success},
        )
        try:
            self._memory.add(entry)
        except Exception as exc:
            context.logger.warning(
                "Failed to record request %r to memory: %s", request.request_id, exc
            )
