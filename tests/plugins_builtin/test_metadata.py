"""Metadata validation tests for mellivor_kernel.plugins_builtin.system_info."""

from __future__ import annotations

from mellivor_kernel.plugins import PluginMetadata
from mellivor_kernel.plugins_builtin import SystemInfoPlugin


def test_metadata_is_a_valid_plugin_metadata() -> None:
    plugin = SystemInfoPlugin()

    metadata = plugin.metadata

    assert isinstance(metadata, PluginMetadata)
    assert metadata.id == "system-info"
    assert metadata.name == "System Information Plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description != ""


def test_metadata_declares_a_kernel_introspection_capability() -> None:
    plugin = SystemInfoPlugin()

    capability_names = {capability.name for capability in plugin.metadata.capabilities}

    assert "kernel.introspection" in capability_names


def test_metadata_is_stable_across_calls() -> None:
    """`metadata` is a property computed fresh each time -- it must be
    equal (value-wise) across repeated access, not just on first read.
    """
    plugin = SystemInfoPlugin()

    assert plugin.metadata == plugin.metadata
