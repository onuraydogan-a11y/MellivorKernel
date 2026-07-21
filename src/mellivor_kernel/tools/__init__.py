"""Public API of the kernel's tool runtime subsystem.

Built-in demonstration tools live in
:mod:`mellivor_kernel.tools.builtin` and are not part of this package's
public surface.
"""

from __future__ import annotations

from mellivor_kernel.tools.base import BaseTool
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.exceptions import ToolError, ToolRegistrationError, ToolValidationError
from mellivor_kernel.tools.metadata import ToolMetadata
from mellivor_kernel.tools.permissions import (
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    KERNEL_INTERNAL,
    NETWORK_READ,
    PROVIDER_INVOKE,
    Permission,
    missing_permissions,
)
from mellivor_kernel.tools.pipeline import ToolExecutionPipeline
from mellivor_kernel.tools.registry import ToolRegistry
from mellivor_kernel.tools.result import ToolResult

__all__ = [
    "FILESYSTEM_READ",
    "FILESYSTEM_WRITE",
    "KERNEL_INTERNAL",
    "NETWORK_READ",
    "PROVIDER_INVOKE",
    "BaseTool",
    "Permission",
    "ToolContext",
    "ToolError",
    "ToolExecutionPipeline",
    "ToolMetadata",
    "ToolRegistrationError",
    "ToolRegistry",
    "ToolResult",
    "ToolValidationError",
    "missing_permissions",
]
