"""The tool execution pipeline: validate -> permission check -> execute ->
result -> logging.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import replace

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.exceptions import ToolValidationError
from mellivor_kernel.tools.permissions import Permission, missing_permissions
from mellivor_kernel.tools.result import ToolResult


class ToolExecutionPipeline:
    """Runs a tool through the kernel's standard execution pipeline.

    The pipeline never lets an exception raised by a tool's own
    ``validate()`` or ``execute()`` propagate out of :meth:`run` -- every
    outcome, including validation failures, permission denials, and
    unexpected exceptions, is translated into a :class:`ToolResult`.
    """

    def run(
        self,
        tool: BaseTool,
        context: ToolContext,
        request: Mapping[str, object],
        *,
        granted_permissions: frozenset[Permission] = frozenset(),
    ) -> ToolResult:
        """Run ``tool`` through validate, permission check, execute, and logging.

        Args:
            tool: The tool to run.
            context: The kernel-provided execution context.
            request: The request payload to validate and execute.
            granted_permissions: The permissions available for this
                execution. Defaults to no permissions granted.

        Returns:
            The outcome of the run. Always returned, never raised, even
            when validation, the permission check, or execution fails.
        """
        try:
            tool.validate(request)
        except ToolValidationError as exc:
            return self._finish(
                context,
                tool,
                ToolResult(success=False, error=str(exc), metadata={"stage": "validate"}),
            )

        missing = missing_permissions(tool.permissions, granted_permissions)
        if missing:
            denied = ", ".join(sorted(permission.value for permission in missing))
            return self._finish(
                context,
                tool,
                ToolResult(
                    success=False,
                    error=f"Missing required permissions: {denied}.",
                    metadata={
                        "stage": "permission_check",
                        "missing_permissions": tuple(
                            sorted(permission.value for permission in missing)
                        ),
                    },
                ),
            )

        started = time.perf_counter()
        try:
            result = tool.execute(context, request)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            return self._finish(
                context,
                tool,
                ToolResult(
                    success=False,
                    error=str(exc),
                    execution_time_seconds=elapsed,
                    metadata={"stage": "execute"},
                ),
            )
        elapsed = time.perf_counter() - started

        return self._finish(context, tool, replace(result, execution_time_seconds=elapsed))

    def _finish(self, context: ToolContext, tool: BaseTool, result: ToolResult) -> ToolResult:
        """Log ``result`` and return it unchanged.

        Args:
            context: The execution context providing the logger.
            tool: The tool that was run.
            result: The outcome to log.

        Returns:
            ``result``, unchanged.
        """
        if result.success:
            context.logger.info(
                "Tool %r executed successfully in %.6fs.",
                tool.id,
                result.execution_time_seconds,
            )
        else:
            context.logger.warning(
                "Tool %r failed at stage %r: %s",
                tool.id,
                result.metadata.get("stage", "unknown"),
                result.error,
            )
        return result
