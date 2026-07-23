"""Dispatches an execution request to its target subsystem."""

from __future__ import annotations

import time

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.exceptions import DispatchError
from mellivor_kernel.execution.request import ExecutionRequest, ExecutionTarget
from mellivor_kernel.execution.result import ExecutionResult
from mellivor_kernel.providers.exceptions import ProviderRegistrationError
from mellivor_kernel.providers.registry import ProviderRegistry
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.exceptions import ToolRegistrationError, ToolValidationError
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.tools.pipeline import ToolExecutionPipeline
from mellivor_kernel.tools.registry import ToolRegistry


class Dispatcher:
    """Dispatches an :class:`ExecutionRequest` to the proper subsystem.

    Current targets are the Tool Runtime (:class:`ToolRegistry` plus
    :class:`ToolExecutionPipeline`) and the Provider Runtime
    (:class:`ProviderRegistry`). This is the only component of the
    execution core that knows about ``tools`` and ``providers`` -- the
    other execution core types (:class:`ExecutionRequest`,
    :class:`ExecutionContext`, :class:`ExecutionResult`) stay agnostic of
    both.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_registry: ProviderRegistry,
        *,
        tool_pipeline: ToolExecutionPipeline | None = None,
    ) -> None:
        """Initialize the dispatcher.

        Args:
            tool_registry: The registry to resolve tools from when
                dispatching to :attr:`ExecutionTarget.TOOL`.
            provider_registry: The registry to resolve providers from when
                dispatching to :attr:`ExecutionTarget.PROVIDER`.
            tool_pipeline: The pipeline to run resolved tools through. A
                new :class:`ToolExecutionPipeline` is created if one is not
                provided.
        """
        self._tool_registry = tool_registry
        self._provider_registry = provider_registry
        self._tool_pipeline = (
            tool_pipeline if tool_pipeline is not None else ToolExecutionPipeline()
        )

    def dispatch(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult:
        """Dispatch ``request`` to its target subsystem.

        Args:
            request: The request to dispatch.
            context: The execution-lifetime context to dispatch with.
            granted_permissions: The permission identifiers (as raw
                strings) available for this dispatch. Only meaningful for
                :attr:`ExecutionTarget.TOOL` -- forwarded to the
                :class:`~mellivor_kernel.tools.pipeline.ToolExecutionPipeline`'s
                own permission check. Ignored for
                :attr:`ExecutionTarget.PROVIDER`, since ``BaseProvider`` has
                no permission model to check against.

        Returns:
            The outcome of the dispatched execution. A failure to resolve
            ``request.operation`` in the target subsystem, an invalid
            permission identifier, or an exception raised while executing
            it, is translated into a failed :class:`ExecutionResult` rather
            than propagated.

        Raises:
            DispatchError: If ``request.target`` names a subsystem this
                dispatcher does not know how to reach.
        """
        if request.target == ExecutionTarget.TOOL:
            return self._dispatch_to_tool(request, context, granted_permissions)
        if request.target == ExecutionTarget.PROVIDER:
            return self._dispatch_to_provider(request, context)
        raise DispatchError(f"No dispatch target registered for {request.target!r}.")

    def _dispatch_to_tool(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        granted_permissions: frozenset[str],
    ) -> ExecutionResult:
        """Resolve and run a tool through the tool execution pipeline."""
        try:
            tool = self._tool_registry.lookup(request.operation)
        except ToolRegistrationError as exc:
            return ExecutionResult(
                success=False,
                error=str(exc),
                metadata={"target": ExecutionTarget.TOOL.value},
            )

        try:
            resolved_permissions = frozenset(Permission(value) for value in granted_permissions)
        except ToolValidationError as exc:
            return ExecutionResult(
                success=False,
                error=str(exc),
                metadata={"target": ExecutionTarget.TOOL.value, "stage": "permission_check"},
            )

        tool_context = ToolContext(
            configuration=context.configuration,
            logger=context.logger,
            runtime=context.runtime,
            services=context.services,
        )
        tool_result = self._tool_pipeline.run(
            tool, tool_context, request.payload, granted_permissions=resolved_permissions
        )

        return ExecutionResult(
            success=tool_result.success,
            payload=tool_result.payload,
            error=tool_result.error,
            execution_time_seconds=tool_result.execution_time_seconds,
            metadata={**tool_result.metadata, "target": ExecutionTarget.TOOL.value},
        )

    def _dispatch_to_provider(
        self, request: ExecutionRequest, context: ExecutionContext
    ) -> ExecutionResult:
        """Resolve and invoke a provider directly."""
        try:
            provider = self._provider_registry.get(request.operation)
        except ProviderRegistrationError as exc:
            return ExecutionResult(
                success=False,
                error=str(exc),
                metadata={"target": ExecutionTarget.PROVIDER.value},
            )

        started = time.perf_counter()
        try:
            response = provider.invoke(request.payload)
        except Exception as exc:  # Translated into a failed result at the boundary, per ADR-0004.
            elapsed = time.perf_counter() - started
            return ExecutionResult(
                success=False,
                error=str(exc),
                execution_time_seconds=elapsed,
                metadata={"target": ExecutionTarget.PROVIDER.value},
            )
        elapsed = time.perf_counter() - started

        return ExecutionResult(
            success=True,
            payload=response,
            execution_time_seconds=elapsed,
            metadata={"target": ExecutionTarget.PROVIDER.value},
        )
