"""RuntimeContext: a read-only view of a bootstrapped kernel runtime."""

from __future__ import annotations

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.logging import get_logger
from mellivor_kernel.core.runtime import HealthStatus, Kernel, KernelState
from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.providers.registry import ProviderRegistry
from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.registry import ToolRegistry


class RuntimeContext:
    """A read-only view of a bootstrapped kernel runtime.

    Exposed to consumers instead of the raw, lifecycle-mutable
    :class:`~mellivor_kernel.core.runtime.Kernel`: it exposes observability
    (:attr:`state`, :meth:`health`) and access to the service container and
    the provider/tool registries, but not ``Kernel.start`` or
    ``Kernel.shutdown``. There is no way to recover the wrapped ``Kernel``
    instance from a ``RuntimeContext``.

    This context is deliberately read-only with respect to the kernel's
    lifecycle: nothing returned by
    :class:`~mellivor_kernel.bootstrap.bootstrap.KernelBootstrap` or
    :class:`~mellivor_kernel.bootstrap.builder.BootstrapBuilder` can stop
    the kernel. If a consuming application needs to shut the kernel down,
    that capability does not exist yet in this sprint's scope.
    """

    def __init__(
        self,
        kernel: Kernel,
        configuration: KernelSettings,
        provider_registry: ProviderRegistry,
        tool_registry: ToolRegistry,
    ) -> None:
        """Initialize the runtime context.

        Args:
            kernel: The bootstrapped kernel runtime to wrap.
            configuration: The configuration this runtime was bootstrapped
                with.
            provider_registry: The provider registry initialized during
                bootstrap.
            tool_registry: The tool registry initialized during bootstrap.
        """
        self._kernel = kernel
        self._configuration = configuration
        self._provider_registry = provider_registry
        self._tool_registry = tool_registry

    @property
    def state(self) -> KernelState:
        """The kernel's current lifecycle state."""
        return self._kernel.state

    def health(self) -> HealthStatus:
        """Return the kernel's current health status.

        Returns:
            A :class:`~mellivor_kernel.core.runtime.HealthStatus`
            reflecting the kernel's current state.
        """
        return self._kernel.health()

    @property
    def configuration(self) -> KernelSettings:
        """The kernel configuration this runtime was bootstrapped with."""
        return self._configuration

    @property
    def services(self) -> ServiceContainer:
        """The kernel's dependency injection container."""
        return self._kernel.container

    @property
    def provider_registry(self) -> ProviderRegistry:
        """The provider registry initialized during bootstrap."""
        return self._provider_registry

    @property
    def tool_registry(self) -> ToolRegistry:
        """The tool registry initialized during bootstrap."""
        return self._tool_registry

    def tool_context(self, *, logger_name: str = "tools") -> ToolContext:
        """Build a :class:`ToolContext` for running tools in this runtime.

        This is the supported way to obtain a ``ToolContext`` from a
        bootstrapped runtime: ``RuntimeContext`` never exposes its wrapped
        ``Kernel`` directly, but can construct a properly formed
        ``ToolContext`` referencing it internally.

        Args:
            logger_name: The name passed to
                :func:`~mellivor_kernel.core.logging.get_logger` for the
                context's logger.

        Returns:
            A new :class:`ToolContext` wrapping this runtime's
            configuration, kernel, and service container.
        """
        return ToolContext(
            configuration=self._configuration,
            logger=get_logger(logger_name),
            runtime=self._kernel,
            services=self._kernel.container,
        )

    def execution_context(self, *, logger_name: str = "execution") -> ExecutionContext:
        """Build an :class:`ExecutionContext` for running executions in this runtime.

        This is the supported way to obtain an ``ExecutionContext`` from a
        bootstrapped runtime, for the same reason
        :meth:`tool_context` exists: ``RuntimeContext`` never exposes its
        wrapped ``Kernel`` directly, but can construct a properly formed
        ``ExecutionContext`` referencing it internally.

        Args:
            logger_name: The name passed to
                :func:`~mellivor_kernel.core.logging.get_logger` for the
                context's logger.

        Returns:
            A new :class:`ExecutionContext` wrapping this runtime's
            configuration, kernel, and service container.
        """
        return ExecutionContext(
            configuration=self._configuration,
            logger=get_logger(logger_name),
            runtime=self._kernel,
            services=self._kernel.container,
        )
