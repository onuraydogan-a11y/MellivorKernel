"""End-to-end example: the system-info built-in plugin, driven through
the complete Plugin SDK + Plugin Runtime path.

`PluginBuilder` (Plugin SDK) builds a manifest, `PluginLoader` (Plugin
Runtime) validates it against the running kernel version and
instantiates the plugin, `PluginRegistry` (Plugin Runtime) registers it,
and `PluginLifecycle` (Plugin Runtime) drives it through
initialize/start/stop/dispose -- the same chain
`tests/test_builtin_plugin_integration.py` proves as pytest assertions.

Run directly: `python examples/plugin_system_info.py`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugin_sdk import PluginBuilder
from mellivor_kernel.plugins import PluginContext, PluginLifecycle, PluginLoader, PluginRegistry
from mellivor_kernel.plugins_builtin import SystemInfoPlugin
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
)
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool, HealthCheckTool, VersionTool
from mellivor_kernel.version import __version__


@dataclass
class _Settings:
    log_level: str = "WARNING"


class _EchoProvider(BaseProvider):
    """Test-only provider satisfying `BaseProvider`. Not a production integration."""

    @property
    def name(self) -> str:
        return "echo-provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echoed": dict(request)}


def main() -> None:
    # A real kernel with real provider/tool registries -- `PluginContext`
    # carries no direct registry fields, so the plugin resolves them from
    # the service container, the same channel bootstrap uses to register
    # them (see `bootstrap.KernelBootstrap._register_default_services`).
    settings = _Settings()
    kernel = Kernel(settings)
    kernel.start()

    provider_registry = ProviderRegistry()
    provider_registry.register(_EchoProvider(ProviderConfiguration(provider_name="echo-provider")))

    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    tool_registry.register(HealthCheckTool())
    tool_registry.register(VersionTool())

    services = ServiceContainer()
    services.register_instance(ProviderRegistry, provider_registry)
    services.register_instance(ToolRegistry, tool_registry)

    context = PluginContext(
        configuration=settings,
        logger=get_logger("plugin_system_info"),
        runtime=kernel,
        services=services,
    )

    # 1. Build a manifest with the Plugin SDK.
    manifest = (
        PluginBuilder()
        .with_id("system-info")
        .with_name("System Information Plugin")
        .with_version("1.0.0")
        .with_author("Mellivor Kernel")
        .with_description("Exposes read-only kernel information.")
        .with_capability("kernel.introspection", "Read-only kernel and runtime information.")
        .with_minimum_kernel_version(__version__)
        .build_manifest()
    )

    # 2. Load: PluginLoader checks kernel-version compatibility, then instantiates.
    loader = PluginLoader(kernel_version=__version__)
    plugin = loader.load(manifest, SystemInfoPlugin)

    # 3. Register.
    registry = PluginRegistry()
    registry.register(plugin)
    print(f"registered plugins: {[metadata.id for metadata in registry.enumerate()]}")

    # 4. Drive the lifecycle.
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(context)
    lifecycle.start()

    snapshot = plugin.collect()
    print(f"kernel_version:        {snapshot.kernel_version}")
    print(f"build_info:            {snapshot.build_info}")
    print(f"available_capabilities: {sorted(snapshot.available_capabilities)}")
    print(f"registered_providers:   {snapshot.registered_providers}")
    print(f"registered_tools:       {snapshot.registered_tools}")
    print(f"runtime_health:         {snapshot.runtime_health}")

    lifecycle.stop()
    lifecycle.dispose()
    print(f"lifecycle state after dispose: {lifecycle.state.value}")


if __name__ == "__main__":
    main()
