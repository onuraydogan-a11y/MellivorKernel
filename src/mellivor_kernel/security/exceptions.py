"""Security exceptions for the kernel's reusable security foundation."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class SecurityError(KernelError):
    """Base class for all security-related kernel errors."""


class SecureConfigurationError(SecurityError):
    """Raised when a secure configuration cannot be resolved or validated."""
