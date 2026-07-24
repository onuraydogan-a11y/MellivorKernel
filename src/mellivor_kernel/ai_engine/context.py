"""AIEngineContext: the shared, kernel-scoped state AIEngine builds every
downstream subsystem context from.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mellivor_kernel.agents import AgentContext
from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.runtime import Kernel
from mellivor_kernel.execution import ExecutionContext
from mellivor_kernel.plugins import PluginContext
from mellivor_kernel.workflow import WorkflowContext


@dataclass(frozen=True, slots=True)
class AIEngineContext:
    """The kernel-scoped state shared by every context `AIEngine` builds.

    The same four fields every kernel-scoped context in this codebase
    already carries (`ExecutionContext`, `ToolContext`, `PluginContext`)
    -- deliberately no more. `AIEngine` builds `ExecutionContext`/
    `WorkflowContext`/`AgentContext`/`PluginContext` from this single
    shared source rather than each caller re-deriving the same four
    fields independently.

    Attributes:
        configuration: The kernel's active settings.
        logger: The default logger used when a context-builder method is
            not given a more specific logger.
        runtime: The kernel runtime instance the engine is running under.
        services: The kernel's dependency injection container.
    """

    configuration: KernelSettings
    logger: logging.Logger
    runtime: Kernel
    services: ServiceContainer

    def to_execution_context(self, *, logger: logging.Logger | None = None) -> ExecutionContext:
        """Build a fresh `ExecutionContext` from this shared state.

        Args:
            logger: Overrides the default logger for this context only.
        """
        return ExecutionContext(
            configuration=self.configuration,
            logger=logger if logger is not None else self.logger,
            runtime=self.runtime,
            services=self.services,
        )

    def to_workflow_context(self, *, logger: logging.Logger | None = None) -> WorkflowContext:
        """Build a fresh `WorkflowContext` wrapping a fresh `ExecutionContext`."""
        return WorkflowContext(execution_context=self.to_execution_context(logger=logger))

    def to_agent_context(self, *, logger: logging.Logger | None = None) -> AgentContext:
        """Build a fresh `AgentContext` wrapping a fresh `WorkflowContext`."""
        return AgentContext(workflow_context=self.to_workflow_context(logger=logger))

    def to_plugin_context(self, *, logger: logging.Logger | None = None) -> PluginContext:
        """Build a fresh `PluginContext` from this shared state.

        Args:
            logger: Overrides the default logger for this context only.
        """
        return PluginContext(
            configuration=self.configuration,
            logger=logger if logger is not None else self.logger,
            runtime=self.runtime,
            services=self.services,
        )
