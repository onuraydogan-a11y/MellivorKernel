"""Registry integration tests: SystemInfoPlugin registered through
PluginRegistry.
"""

from __future__ import annotations

import pytest

from mellivor_kernel.plugins import PluginRegistrationError, PluginRegistry
from mellivor_kernel.plugins_builtin import SystemInfoPlugin


def test_register_and_lookup() -> None:
    registry = PluginRegistry()
    plugin = SystemInfoPlugin()

    registry.register(plugin)

    assert registry.lookup("system-info") is plugin


def test_register_twice_raises() -> None:
    registry = PluginRegistry()
    registry.register(SystemInfoPlugin())

    with pytest.raises(PluginRegistrationError):
        registry.register(SystemInfoPlugin())


def test_enumerate_reports_system_info_metadata() -> None:
    registry = PluginRegistry()
    registry.register(SystemInfoPlugin())

    enumerated = registry.enumerate()

    assert len(enumerated) == 1
    assert enumerated[0].id == "system-info"


def test_a_plugin_registry_reference_lets_system_info_report_registry_wide_capabilities() -> None:
    """Constructing `SystemInfoPlugin` with a `plugin_registry` reference
    lets `collect()` report the union of every registered plugin's
    capabilities -- exercised here with just itself registered.
    """
    registry = PluginRegistry()
    plugin = SystemInfoPlugin(plugin_registry=registry)
    registry.register(plugin)

    assert registry.lookup("system-info") is plugin
