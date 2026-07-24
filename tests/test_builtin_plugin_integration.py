"""End-to-end test: the system-info built-in plugin driven through the
complete Plugin SDK + Plugin Runtime path -- PluginBuilder to build a
manifest, PluginLoader to validate and instantiate, PluginRegistry to
register, and PluginLifecycle to run it against a real Kernel with real
provider/tool registries.

Mirrors `tests/test_tool_bootstrap.py`'s end-to-end style for the Tool
Runtime, exercised here as pytest assertions for the Plugin Runtime and
Plugin SDK (Sprints 18-20) instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugin_sdk import PluginBuilder
from mellivor_kernel.plugins import (
    PluginContext,
    PluginLifecycle,
    PluginLifecycleState,
    PluginLoader,
    PluginLoadError,
    PluginRegistry,
)
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
class _FakeSettings:
    log_level: str = "INFO"


class _EchoProvider(BaseProvider):
    """Test-only provider satisfying `BaseProvider`. Not a production integration."""

    @property
    def name(self) -> str:
        return "echo-provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=False)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echoed": dict(request)}


def test_system_info_plugin_end_to_end() -> None:
    # Real kernel, real provider/tool registries -- not fakes.
    settings = _FakeSettings()
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
        logger=get_logger("test_builtin_plugin_integration"),
        runtime=kernel,
        services=services,
    )

    # 1. Instantiate a manifest using the Plugin SDK's PluginBuilder.
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

    # 2. Load through PluginLoader -- validates kernel-version compatibility,
    #    then instantiates.
    loader = PluginLoader(kernel_version=__version__)
    plugin = loader.load(manifest, SystemInfoPlugin)
    assert isinstance(plugin, SystemInfoPlugin)

    # 3. Register through PluginRegistry.
    plugin_registry = PluginRegistry()
    plugin_registry.register(plugin)
    assert plugin_registry.lookup("system-info") is plugin
    assert [metadata.id for metadata in plugin_registry.enumerate()] == ["system-info"]

    # 4. Drive the full lifecycle through PluginLifecycle.
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(context)
    lifecycle.start()

    snapshot = plugin.collect()

    assert snapshot.kernel_version == __version__
    assert "Python" in snapshot.build_info
    assert "kernel.introspection" in snapshot.available_capabilities
    assert snapshot.registered_providers == ("echo-provider",)
    assert set(snapshot.registered_tools) == {"echo", "health_check", "version"}
    assert snapshot.runtime_health.healthy is True

    lifecycle.stop()
    lifecycle.dispose()
    assert lifecycle.state == PluginLifecycleState.DISPOSED


def test_system_info_plugin_rejects_incompatible_kernel_version_end_to_end() -> None:
    manifest = (
        PluginBuilder()
        .with_id("system-info")
        .with_name("System Information Plugin")
        .with_version("1.0.0")
        .with_author("Mellivor Kernel")
        .with_minimum_kernel_version("999.0.0")
        .build_manifest()
    )
    loader = PluginLoader(kernel_version=__version__)

    try:
        loader.load(manifest, SystemInfoPlugin)
    except PluginLoadError as exc:
        assert "999.0.0" in str(exc)
        assert __version__ in str(exc)
    else:
        raise AssertionError("expected PluginLoadError")
