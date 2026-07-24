"""Runtime loading tests: SystemInfoPlugin loaded through PluginLoader."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugin_sdk import create_manifest
from mellivor_kernel.plugins import PluginLoader, PluginLoadError, PluginManifest
from mellivor_kernel.plugins_builtin import SystemInfoPlugin
from mellivor_kernel.version import __version__


def _make_manifest(minimum_kernel_version: str = "0.0.0") -> PluginManifest:
    plugin = SystemInfoPlugin()
    return create_manifest(
        id=plugin.metadata.id,
        name=plugin.metadata.name,
        version=plugin.metadata.version,
        author="Mellivor Kernel",
        description=plugin.metadata.description,
        minimum_kernel_version=minimum_kernel_version,
    )


def test_loader_instantiates_system_info_plugin() -> None:
    loader = PluginLoader(kernel_version=__version__)
    manifest = _make_manifest(minimum_kernel_version=__version__)

    plugin = loader.load(manifest, SystemInfoPlugin)

    assert isinstance(plugin, SystemInfoPlugin)
    assert plugin.metadata.id == "system-info"


def test_loader_accepts_an_older_minimum_kernel_version() -> None:
    loader = PluginLoader(kernel_version=__version__)
    manifest = _make_manifest(minimum_kernel_version="0.1.0")

    plugin = loader.load(manifest, SystemInfoPlugin)

    assert isinstance(plugin, SystemInfoPlugin)


def test_loader_rejects_a_manifest_newer_than_the_running_kernel() -> None:
    loader = PluginLoader(kernel_version=__version__)
    manifest = _make_manifest(minimum_kernel_version="999.0.0")

    with pytest.raises(PluginLoadError):
        loader.load(manifest, SystemInfoPlugin)


def test_loader_defaults_to_the_installed_kernel_version() -> None:
    loader = PluginLoader()
    manifest = _make_manifest(minimum_kernel_version=__version__)

    plugin = loader.load(manifest, SystemInfoPlugin)

    assert isinstance(plugin, SystemInfoPlugin)
