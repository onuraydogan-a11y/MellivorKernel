"""Tests for mellivor_kernel.plugins.loader."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginLoader,
    PluginLoadError,
    PluginManifest,
    PluginMetadata,
)
from mellivor_kernel.version import __version__


class _FakePlugin(Plugin):
    def __init__(self, plugin_id: str = "example") -> None:
        self._id = plugin_id

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id=self._id, name="Example", version="1.0.0", description="")

    def initialize(self, context: PluginContext) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass


def _make_manifest(**overrides: object) -> PluginManifest:
    fields: dict[str, object] = {
        "id": "example",
        "name": "Example",
        "version": "1.0.0",
        "description": "",
        "author": "Someone",
        "minimum_kernel_version": "0.0.0",
    }
    fields.update(overrides)
    return PluginManifest(**fields)  # type: ignore[arg-type]


def test_loader_instantiates_a_compatible_plugin() -> None:
    loader = PluginLoader(kernel_version="0.13.0")
    manifest = _make_manifest(minimum_kernel_version="0.13.0")

    plugin = loader.load(manifest, _FakePlugin)

    assert isinstance(plugin, _FakePlugin)
    assert plugin.metadata.id == "example"


def test_loader_accepts_a_manifest_older_than_the_running_kernel() -> None:
    loader = PluginLoader(kernel_version="0.13.0")
    manifest = _make_manifest(minimum_kernel_version="0.5.0")

    plugin = loader.load(manifest, _FakePlugin)

    assert isinstance(plugin, _FakePlugin)


def test_loader_rejects_a_manifest_newer_than_the_running_kernel() -> None:
    loader = PluginLoader(kernel_version="0.13.0")
    manifest = _make_manifest(minimum_kernel_version="1.0.0")

    with pytest.raises(PluginLoadError) as excinfo:
        loader.load(manifest, _FakePlugin)

    assert "example" in str(excinfo.value)
    assert "1.0.0" in str(excinfo.value)
    assert "0.13.0" in str(excinfo.value)


def test_loader_wraps_a_failing_factory() -> None:
    loader = PluginLoader(kernel_version="0.13.0")
    manifest = _make_manifest()

    def _broken_factory() -> Plugin:
        raise RuntimeError("boom")

    with pytest.raises(PluginLoadError) as excinfo:
        loader.load(manifest, _broken_factory)

    assert "example" in str(excinfo.value)
    assert "boom" in str(excinfo.value)


def test_loader_rejects_a_plugin_whose_id_does_not_match_the_manifest() -> None:
    loader = PluginLoader(kernel_version="0.13.0")
    manifest = _make_manifest(id="expected-id")

    with pytest.raises(PluginLoadError):
        loader.load(manifest, lambda: _FakePlugin("different-id"))


def test_loader_defaults_kernel_version_to_the_installed_package_version() -> None:
    loader = PluginLoader()
    manifest = _make_manifest(minimum_kernel_version=__version__)

    plugin = loader.load(manifest, _FakePlugin)

    assert isinstance(plugin, _FakePlugin)
