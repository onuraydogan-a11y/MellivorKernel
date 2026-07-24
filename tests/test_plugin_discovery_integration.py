"""End-to-end test: discovering the real, already-shipped `SystemInfoPlugin`
(Sprint 20) from a real filesystem location, through the complete
PluginDiscovery -> PluginLoader -> PluginRegistry -> PluginLifecycle path.

Mirrors `tests/test_builtin_plugin_integration.py`'s end-to-end style,
exercised here with a manifest file on disk instead of a
`PluginBuilder`-constructed manifest, proving Sprint 21's discovery layer
composes with Sprints 18-20 without any change to them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugin_discovery import PluginDiscovery
from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginLifecycle,
    PluginLoader,
    PluginMetadata,
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
from mellivor_kernel.tools.builtin import EchoTool
from mellivor_kernel.version import __version__


@dataclass
class _Settings:
    log_level: str = "WARNING"


class _SecondPlugin(Plugin):
    """A second, minimal plugin, module-level so it is importable by its
    own entry point -- proves multi-plugin discovery alongside the real
    `SystemInfoPlugin` without needing a second instance of it.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="second-plugin", name="Second Plugin", version="1.0.0", description=""
        )

    def initialize(self, context: PluginContext) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass


class _EchoProvider(BaseProvider):
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


def _write_system_info_manifest(root: Path) -> None:
    plugin_dir = root / "system-info"
    plugin_dir.mkdir(parents=True)
    manifest = {
        "id": "system-info",
        "name": "System Information Plugin",
        "version": "1.0.0",
        "description": "Exposes read-only kernel information.",
        "author": "Mellivor Kernel",
        "minimum_kernel_version": __version__,
        "capabilities": [
            {
                "name": "kernel.introspection",
                "description": "Read-only kernel and runtime information.",
            }
        ],
        "entry_point": "mellivor_kernel.plugins_builtin.system_info:SystemInfoPlugin",
    }
    (plugin_dir / "plugin_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_system_info_plugin_discovered_from_filesystem_end_to_end(tmp_path: Path) -> None:
    _write_system_info_manifest(tmp_path)

    settings = _Settings()
    kernel = Kernel(settings)
    kernel.start()

    provider_registry = ProviderRegistry()
    provider_registry.register(_EchoProvider(ProviderConfiguration(provider_name="echo-provider")))
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())

    services = ServiceContainer()
    services.register_instance(ProviderRegistry, provider_registry)
    services.register_instance(ToolRegistry, tool_registry)

    context = PluginContext(
        configuration=settings,
        logger=get_logger("test_plugin_discovery_integration"),
        runtime=kernel,
        services=services,
    )

    discovery = PluginDiscovery(PluginLoader(kernel_version=__version__))
    registry = PluginRegistry()

    discovered = discovery.discover_and_register(tmp_path, registry)

    assert [p.metadata.id for p in discovered] == ["system-info"]
    plugin = registry.lookup("system-info")
    assert isinstance(plugin, SystemInfoPlugin)

    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(context)
    lifecycle.start()

    snapshot = plugin.collect()
    assert snapshot.kernel_version == __version__
    assert "kernel.introspection" in snapshot.available_capabilities
    assert snapshot.registered_providers == ("echo-provider",)
    assert snapshot.registered_tools == ("echo",)
    assert snapshot.runtime_health.healthy is True

    lifecycle.stop()
    lifecycle.dispose()


def test_discovery_of_multiple_plugins_is_deterministic_and_independent(tmp_path: Path) -> None:
    """Two distinct plugin directories under the same root are both
    discovered and registered, without either affecting the other.
    """
    _write_system_info_manifest(tmp_path)
    second_dir = tmp_path / "second-plugin"
    second_dir.mkdir()
    manifest = {
        "id": "second-plugin",
        "name": "Second Plugin",
        "version": "1.0.0",
        "author": "Mellivor Kernel",
        "minimum_kernel_version": __version__,
        "entry_point": "tests.test_plugin_discovery_integration:_SecondPlugin",
    }
    (second_dir / "plugin_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    discovery = PluginDiscovery(PluginLoader(kernel_version=__version__))
    registry = PluginRegistry()

    discovered = discovery.discover_and_register(tmp_path, registry)

    assert {p.metadata.id for p in discovered} == {"system-info", "second-plugin"}
    assert registry.exists("system-info") is True
    assert registry.exists("second-plugin") is True
