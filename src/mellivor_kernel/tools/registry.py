"""A registry of tool instances, keyed by tool id."""

from __future__ import annotations

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.exceptions import ToolRegistrationError
from mellivor_kernel.tools.metadata import ToolMetadata


class ToolRegistry:
    """A registry of :class:`BaseTool` instances, keyed by each tool's own
    :attr:`~BaseTool.id`.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance under its own ``id``.

        Args:
            tool: The tool instance to register.

        Raises:
            ToolRegistrationError: If a tool is already registered under
                ``tool.id``.
        """
        tool_id = tool.id
        if tool_id in self._tools:
            raise ToolRegistrationError(f"Tool {tool_id!r} is already registered.")
        self._tools[tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        """Remove a registered tool.

        Args:
            tool_id: The id of the tool to remove.

        Raises:
            ToolRegistrationError: If no tool is registered under
                ``tool_id``.
        """
        try:
            del self._tools[tool_id]
        except KeyError as exc:
            raise ToolRegistrationError(f"Tool {tool_id!r} is not registered.") from exc

    def lookup(self, tool_id: str) -> BaseTool:
        """Resolve a registered tool by id.

        Args:
            tool_id: The id of the tool to look up.

        Returns:
            The registered tool instance.

        Raises:
            ToolRegistrationError: If no tool is registered under
                ``tool_id``.
        """
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise ToolRegistrationError(f"Tool {tool_id!r} is not registered.") from exc

    def exists(self, tool_id: str) -> bool:
        """Return whether a tool is registered under ``tool_id``.

        Args:
            tool_id: The id to check.

        Returns:
            ``True`` if a tool was registered under ``tool_id`` via
            :meth:`register`, ``False`` otherwise.
        """
        return tool_id in self._tools

    def enumerate(self) -> tuple[ToolMetadata, ...]:
        """Return metadata for every currently registered tool.

        Returns:
            A tuple of :class:`ToolMetadata`, one per registered tool, in
            registration order.
        """
        return tuple(tool.metadata() for tool in self._tools.values())
