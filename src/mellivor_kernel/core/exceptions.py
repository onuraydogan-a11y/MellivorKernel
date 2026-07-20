"""Kernel-wide exception hierarchy.

Every exception Mellivor Kernel raises from its own code derives from
:class:`KernelError`, so callers can catch kernel-originated failures
without needing to know which subsystem raised them.
"""

from __future__ import annotations


class KernelError(Exception):
    """Base class for all errors raised by Mellivor Kernel."""


class ConfigurationError(KernelError):
    """Raised when kernel configuration is missing, malformed, or invalid."""


class ServiceRegistrationError(KernelError):
    """Raised when a service cannot be registered with, or resolved from, the container."""


class StartupError(KernelError):
    """Raised when the kernel fails to complete its startup sequence."""
