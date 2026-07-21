"""Tool subsystem exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class ToolError(KernelError):
    """Base class for all errors raised by the tools subsystem."""


class ToolRegistrationError(ToolError):
    """Raised when a tool cannot be registered with, or resolved from, a registry."""


class ToolValidationError(ToolError):
    """Raised when a permission identifier or a tool execution request is invalid."""
