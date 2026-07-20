"""Provider subsystem exception hierarchy.

All exceptions here derive from
:class:`~mellivor_kernel.core.exceptions.KernelError`, consistent with the
kernel-wide contract that every exception the kernel raises can be caught
as a ``KernelError`` regardless of which subsystem raised it.
"""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class ProviderError(KernelError):
    """Base class for all errors raised by the providers subsystem."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is missing, malformed, or invalid."""


class ProviderRegistrationError(ProviderError):
    """Raised when a provider cannot be registered with, or resolved from, a registry or factory."""
