"""Bootstrap subsystem exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class BootstrapError(KernelError):
    """Raised when assembling a kernel runtime fails for any reason."""
