"""Public API of the kernel's core subsystem."""

from __future__ import annotations

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.exceptions import (
    ConfigurationError,
    KernelError,
    ServiceRegistrationError,
    StartupError,
)
from mellivor_kernel.core.logging import (
    StructuredFormatter,
    add_file_handler,
    configure_logging,
    get_logger,
)
from mellivor_kernel.core.runtime import HealthStatus, Kernel, KernelState

__all__ = [
    "ConfigurationError",
    "HealthStatus",
    "Kernel",
    "KernelError",
    "KernelSettings",
    "KernelState",
    "ServiceContainer",
    "ServiceRegistrationError",
    "StartupError",
    "StructuredFormatter",
    "add_file_handler",
    "configure_logging",
    "get_logger",
]
