"""HealthCheckTool: reports the kernel runtime's current health."""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL, Permission
from mellivor_kernel.tools.result import ToolResult


class HealthCheckTool(BaseTool):
    """Reports the current health status of the kernel runtime.

    Demonstrates a tool that reads from the execution context's
    ``runtime`` and requires a non-trivial permission
    (``kernel.internal``).
    """

    @property
    def id(self) -> str:
        """A short, unique identifier for this tool."""
        return "health_check"

    @property
    def name(self) -> str:
        """A human-readable name."""
        return "Health Check Tool"

    @property
    def version(self) -> str:
        """This tool's own version string."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """A human-readable description of what this tool does."""
        return "Reports the current health status of the kernel runtime."

    @property
    def capabilities(self) -> frozenset[str]:
        """Free-form tags describing what this tool can do."""
        return frozenset({"diagnostic", "observability"})

    @property
    def permissions(self) -> frozenset[Permission]:
        """The permissions this tool requires to execute."""
        return frozenset({KERNEL_INTERNAL})

    def validate(self, request: Mapping[str, object]) -> None:
        """Accept any request; the health check takes no input.

        Args:
            request: Ignored.
        """
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        """Return the kernel runtime's current health as the result payload.

        Args:
            context: The kernel-provided execution context.
            request: Ignored.

        Returns:
            A successful result whose payload describes the kernel's
            current health.
        """
        health = context.runtime.health()
        return ToolResult(
            success=True,
            payload={
                "healthy": health.healthy,
                "state": health.state.value,
                "detail": health.detail,
            },
        )
