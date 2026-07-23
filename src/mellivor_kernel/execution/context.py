"""The execution lifetime context."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.runtime import Kernel


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """The kernel-scoped state available for the lifetime of one execution.

    Deliberately kernel-scoped only: it carries no business data and no
    knowledge of any specific tool or provider. A dispatch target that needs
    a subsystem-specific context (for example a
    :class:`~mellivor_kernel.tools.context.ToolContext`) builds it from this
    context's fields rather than this type growing subsystem-specific
    attributes.

    Attributes:
        configuration: The kernel's active settings.
        logger: A logger scoped for execution.
        runtime: The kernel runtime instance the execution is running under.
        services: The kernel's dependency injection container, for dispatch
            targets that need to resolve a registered service.
    """

    configuration: KernelSettings
    logger: logging.Logger
    runtime: Kernel
    services: ServiceContainer
