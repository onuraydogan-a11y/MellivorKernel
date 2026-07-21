"""EchoTool: a minimal demonstration tool that echoes its request back."""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.tools.result import ToolResult


class EchoTool(BaseTool):
    """Echoes the given request payload back unchanged.

    Exists to validate the tool runtime end-to-end with the simplest
    possible tool: no permissions required, no external state touched.
    """

    @property
    def id(self) -> str:
        """A short, unique identifier for this tool."""
        return "echo"

    @property
    def name(self) -> str:
        """A human-readable name."""
        return "Echo Tool"

    @property
    def version(self) -> str:
        """This tool's own version string."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """A human-readable description of what this tool does."""
        return "Echoes the given request payload back unchanged."

    @property
    def capabilities(self) -> frozenset[str]:
        """Free-form tags describing what this tool can do."""
        return frozenset({"diagnostic"})

    @property
    def permissions(self) -> frozenset[Permission]:
        """The permissions this tool requires to execute."""
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        """Accept any request; echoing has no input constraints.

        Args:
            request: The request payload to be echoed back.
        """
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        """Return ``request`` unchanged as the result payload.

        Args:
            context: The kernel-provided execution context (unused).
            request: The request payload to echo back.

        Returns:
            A successful result whose payload is a copy of ``request``.
        """
        return ToolResult(success=True, payload=dict(request))
