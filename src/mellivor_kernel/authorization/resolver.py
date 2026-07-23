"""PermissionResolver: determines the permissions required for an operation."""

from __future__ import annotations

from mellivor_kernel.authorization.permission_set import PermissionSet
from mellivor_kernel.execution.request import ExecutionTarget
from mellivor_kernel.tools.exceptions import ToolRegistrationError
from mellivor_kernel.tools.registry import ToolRegistry


class PermissionResolver:
    """Resolves the permissions required to run a given target/operation.

    The only place this subsystem consults the Tool Runtime -- and only to
    read a tool's already-declared :attr:`~mellivor_kernel.tools.base.BaseTool.permissions`,
    never to register, unregister, or execute anything.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        """Initialize the resolver.

        Args:
            tool_registry: The registry to look up a tool's declared
                permissions from, for :attr:`ExecutionTarget.TOOL`
                operations.
        """
        self._tool_registry = tool_registry

    def resolve_required_permissions(
        self, target: ExecutionTarget, operation: str
    ) -> PermissionSet:
        """Return the permissions required to run ``operation`` on ``target``.

        Args:
            target: Which subsystem ``operation`` would be dispatched to.
            operation: The tool id or provider name to resolve
                requirements for.

        Returns:
            ``operation``'s declared :class:`PermissionSet` when ``target``
            is :attr:`ExecutionTarget.TOOL` and the tool is registered.
            Empty otherwise -- :attr:`ExecutionTarget.PROVIDER` has no
            permission model in the current ``BaseProvider`` contract, and
            an unregistered tool has no declared requirements this
            resolver can read; the dispatcher (not authorization) is
            responsible for reporting "no such tool" as a dispatch
            failure.
        """
        if target != ExecutionTarget.TOOL:
            return PermissionSet.empty()

        try:
            tool = self._tool_registry.lookup(operation)
        except ToolRegistrationError:
            return PermissionSet.empty()

        return PermissionSet(tool.permissions)
