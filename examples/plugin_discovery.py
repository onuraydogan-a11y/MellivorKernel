"""End-to-end example: Plugin Discovery Foundation.

Discovers the `system-info` sample plugin from
`examples/sample_plugins/` -- a real filesystem location containing a
manifest file naming the already-shipped
`plugins_builtin.SystemInfoPlugin` as its entry point -- loads it
through `PluginLoader`, registers it through `PluginRegistry`, and
drives it through the same lifecycle
`examples/plugin_system_info.py` already demonstrates by hand, without
this script ever constructing a `PluginManifest` or importing
`SystemInfoPlugin` directly.

Run directly: `python examples/plugin_discovery.py`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugin_discovery import PluginDiscovery
from mellivor_kernel.plugins import PluginContext, PluginLifecycle, PluginLoader, PluginRegistry
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
        logger=get_logger("plugin_discovery_example"),
        runtime=kernel,
        services=services,
    )

    # Discover, load, and register every plugin under sample_plugins/ --
    # no PluginManifest or SystemInfoPlugin import needed here at all.
    discovery = PluginDiscovery(PluginLoader(kernel_version=__version__))
    registry = PluginRegistry()
    sample_plugins_root = Path(__file__).parent / "sample_plugins"

    discovered = discovery.discover_and_register(sample_plugins_root, registry)
    print(f"discovered and registered: {[p.metadata.id for p in discovered]}")

    plugin = registry.lookup("system-info")
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(context)
    lifecycle.start()

    snapshot = plugin.collect()  # type: ignore[attr-defined]
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
