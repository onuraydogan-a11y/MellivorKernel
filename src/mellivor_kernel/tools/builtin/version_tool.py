"""VersionTool: reports the installed Mellivor Kernel package version."""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.tools.result import ToolResult
from mellivor_kernel.version import __version__


class VersionTool(BaseTool):
    """Reports the installed Mellivor Kernel package version.

    Demonstrates a tool with no dependency on the execution context at
    all: its output depends only on the installed package.
    """

    @property
    def id(self) -> str:
        """A short, unique identifier for this tool."""
        return "version"

    @property
    def name(self) -> str:
        """A human-readable name."""
        return "Version Tool"

    @property
    def version(self) -> str:
        """This tool's own version string."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """A human-readable description of what this tool does."""
        return "Reports the installed Mellivor Kernel package version."

    @property
    def capabilities(self) -> frozenset[str]:
        """Free-form tags describing what this tool can do."""
        return frozenset({"diagnostic"})

    @property
    def permissions(self) -> frozenset[Permission]:
        """The permissions this tool requires to execute."""
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        """Accept any request; reporting the version takes no input.

        Args:
            request: Ignored.
        """
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        """Return the kernel package version as the result payload.

        Args:
            context: The kernel-provided execution context (unused).
            request: Ignored.

        Returns:
            A successful result whose payload contains the installed
            ``mellivor_kernel`` package version.
        """
        return ToolResult(success=True, payload={"version": __version__})
