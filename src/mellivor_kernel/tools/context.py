"""The tool execution context."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.runtime import Kernel


@dataclass(frozen=True, slots=True)
class ToolContext:
    """The execution context every tool receives when run.

    Deliberately kernel-scoped only: it carries no business data. A tool
    that needs business-specific input receives it via the ``request``
    argument to :meth:`~mellivor_kernel.tools.base.BaseTool.execute`, not
    through this context.

    Attributes:
        configuration: The kernel's active settings.
        logger: A logger scoped for tool execution.
        runtime: The kernel runtime instance the tool is executing under.
        services: The kernel's dependency injection container, for tools
            that need to resolve a registered service.
    """

    configuration: KernelSettings
    logger: logging.Logger
    runtime: Kernel
    services: ServiceContainer
