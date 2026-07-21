"""BootstrapBuilder: a fluent builder for assembling a kernel runtime."""

from __future__ import annotations

from typing import Any, TypeVar

from mellivor_kernel.bootstrap.bootstrap import KernelBootstrap
from mellivor_kernel.bootstrap.context import RuntimeContext
from mellivor_kernel.config.settings import KernelConfig
from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.providers.registry import ProviderRegistry
from mellivor_kernel.tools.registry import ToolRegistry

T = TypeVar("T")


class BootstrapBuilder:
    """A fluent builder for assembling a kernel runtime.

    Lets an application override any of
    :class:`~mellivor_kernel.bootstrap.bootstrap.KernelBootstrap`'s default
    components -- the service container, the provider registry, the tool
    registry, or individual extra services -- before bootstrap runs.
    """

    def __init__(self, config: KernelConfig) -> None:
        """Initialize the builder.

        Args:
            config: The kernel configuration to boot with.
        """
        self._config = config
        self._container: ServiceContainer | None = None
        self._provider_registry: ProviderRegistry | None = None
        self._tool_registry: ToolRegistry | None = None
        self._extra_services: dict[type[Any], Any] = {}
        self._register_builtin_tools = False

    def with_container(self, container: ServiceContainer) -> BootstrapBuilder:
        """Use ``container`` instead of a newly created one.

        Args:
            container: The service container to use.

        Returns:
            This builder, for chaining.
        """
        self._container = container
        return self

    def with_provider_registry(self, registry: ProviderRegistry) -> BootstrapBuilder:
        """Use ``registry`` instead of a newly created one.

        Args:
            registry: The provider registry to use.

        Returns:
            This builder, for chaining.
        """
        self._provider_registry = registry
        return self

    def with_tool_registry(self, registry: ToolRegistry) -> BootstrapBuilder:
        """Use ``registry`` instead of a newly created one.

        Args:
            registry: The tool registry to use.

        Returns:
            This builder, for chaining.
        """
        self._tool_registry = registry
        return self

    def with_service(self, service_type: type[T], instance: T) -> BootstrapBuilder:
        """Register an additional service, beyond the kernel's own defaults.

        Args:
            service_type: The type other code will use to look up this
                service.
            instance: The instance to register.

        Returns:
            This builder, for chaining.
        """
        self._extra_services[service_type] = instance
        return self

    def with_builtin_tools(self) -> BootstrapBuilder:
        """Register the kernel's built-in demonstration tools.

        Registers ``EchoTool``, ``HealthCheckTool``, and ``VersionTool``
        into the tool registry during bootstrap.

        Returns:
            This builder, for chaining.
        """
        self._register_builtin_tools = True
        return self

    def build(self) -> RuntimeContext:
        """Run the bootstrap sequence with the accumulated overrides.

        Returns:
            A :class:`~mellivor_kernel.bootstrap.context.RuntimeContext`
            wrapping the started kernel.

        Raises:
            BootstrapError: If bootstrap fails for any reason.
        """
        return KernelBootstrap.run(
            self._config,
            container=self._container,
            provider_registry=self._provider_registry,
            tool_registry=self._tool_registry,
            extra_services=self._extra_services or None,
            register_builtin_tools=self._register_builtin_tools,
        )
