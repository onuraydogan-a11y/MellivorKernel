"""PluginContext: the kernel-scoped context a plugin executes with."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.runtime import Kernel


@dataclass(frozen=True, slots=True)
class PluginContext:
    """The kernel-scoped state a plugin is given at `initialize()`.

    Deliberately kernel-scoped only, the same four fields as
    `execution.ExecutionContext` and `tools.ToolContext` -- a plugin
    receives no business data and no knowledge of any specific tool,
    provider, or product feature through this context.

    Attributes:
        configuration: The kernel's active settings.
        logger: A logger scoped for this plugin.
        runtime: The kernel runtime instance the plugin is running under.
        services: The kernel's dependency injection container, for a
            plugin that needs to resolve a registered service.
    """

    configuration: KernelSettings
    logger: logging.Logger
    runtime: Kernel
    services: ServiceContainer
