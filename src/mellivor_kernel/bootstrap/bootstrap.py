"""KernelBootstrap: the kernel's default bootstrap sequence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mellivor_kernel.bootstrap.context import RuntimeContext
from mellivor_kernel.bootstrap.exceptions import BootstrapError
from mellivor_kernel.config.settings import KernelConfig
from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.exceptions import KernelError
from mellivor_kernel.core.runtime import Kernel
from mellivor_kernel.providers.registry import ProviderRegistry
from mellivor_kernel.tools.builtin import EchoTool, HealthCheckTool, VersionTool
from mellivor_kernel.tools.registry import ToolRegistry


class KernelBootstrap:
    """The kernel's default bootstrap sequence.

    Builds a :class:`~mellivor_kernel.core.runtime.Kernel` from a
    :class:`~mellivor_kernel.config.settings.KernelConfig`, creates (or
    accepts) a service container, registers the kernel's default services
    into it, initializes the provider and tool registries, starts the
    kernel, and returns a read-only :class:`~mellivor_kernel.bootstrap.context.RuntimeContext`.
    """

    @staticmethod
    def run(
        config: KernelConfig,
        *,
        container: ServiceContainer | None = None,
        provider_registry: ProviderRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
        extra_services: Mapping[type[Any], Any] | None = None,
        register_builtin_tools: bool = False,
    ) -> RuntimeContext:
        """Assemble and start a kernel runtime.

        Args:
            config: The kernel configuration to boot with.
            container: The service container to use. A new, empty
                container is created if one is not provided.
            provider_registry: The provider registry to use. A new, empty
                registry is created if one is not provided.
            tool_registry: The tool registry to use. A new, empty registry
                is created if one is not provided.
            extra_services: Additional services to register into the
                container, beyond the kernel's own defaults.
            register_builtin_tools: If ``True``, register the kernel's
                built-in demonstration tools (``EchoTool``,
                ``HealthCheckTool``, ``VersionTool``) into the tool
                registry. Defaults to ``False``: the tool registry is
                otherwise initialized empty, matching how the provider
                registry is initialized (there are no concrete providers
                to register either).

        Returns:
            A :class:`~mellivor_kernel.bootstrap.context.RuntimeContext`
            wrapping the started kernel.

        Raises:
            BootstrapError: If any step of the bootstrap sequence fails,
                including a colliding service registration or the kernel
                failing to start. The original error is chained via
                ``__cause__``.
        """
        try:
            resolved_container = container if container is not None else ServiceContainer()
            resolved_provider_registry = (
                provider_registry if provider_registry is not None else ProviderRegistry()
            )
            resolved_tool_registry = tool_registry if tool_registry is not None else ToolRegistry()

            if register_builtin_tools:
                for tool in (EchoTool(), HealthCheckTool(), VersionTool()):
                    resolved_tool_registry.register(tool)

            _register_default_services(
                resolved_container, config, resolved_provider_registry, resolved_tool_registry
            )
            if extra_services:
                for service_type, instance in extra_services.items():
                    resolved_container.register_instance(service_type, instance)

            kernel = Kernel(config, container=resolved_container)
            kernel.start()
        except KernelError as exc:
            raise BootstrapError(f"Kernel bootstrap failed: {exc}") from exc

        return RuntimeContext(
            kernel=kernel,
            configuration=config,
            provider_registry=resolved_provider_registry,
            tool_registry=resolved_tool_registry,
        )


def _register_default_services(
    container: ServiceContainer,
    config: KernelConfig,
    provider_registry: ProviderRegistry,
    tool_registry: ToolRegistry,
) -> None:
    """Register the kernel's default services into ``container``.

    Args:
        container: The service container to register into.
        config: The kernel configuration to register.
        provider_registry: The provider registry to register.
        tool_registry: The tool registry to register.

    Raises:
        ServiceRegistrationError: If any of these types are already
            registered in ``container``.
    """
    container.register_instance(KernelConfig, config)
    container.register_instance(ProviderRegistry, provider_registry)
    container.register_instance(ToolRegistry, tool_registry)
