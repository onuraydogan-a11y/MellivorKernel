"""Tests for mellivor_kernel.plugin_discovery.discovery.PluginDiscovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mellivor_kernel.plugin_discovery import (
    EntryPointError,
    ManifestNotFoundError,
    PluginDiscovery,
    PluginDiscoveryError,
)
from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginLoader,
    PluginLoadError,
    PluginMetadata,
    PluginRegistrationError,
    PluginRegistry,
)
from mellivor_kernel.version import __version__


class _FakePlugin(Plugin):
    """A minimal, module-level `Plugin` so its qualified name is
    importable by `resolve_entry_point()`.
    """

    def __init__(self) -> None:
        self.initialized = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id="fake", name="Fake Plugin", version="1.0.0", description="")

    def initialize(self, context: PluginContext) -> None:
        self.initialized = True

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass


class _MismatchedIdPlugin(Plugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id="different-id", name="X", version="1.0.0", description="")

    def initialize(self, context: PluginContext) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass


def _write_plugin_dir(
    parent: Path, dir_name: str, *, entry_point: str, plugin_id: str = "fake"
) -> Path:
    plugin_dir = parent / dir_name
    plugin_dir.mkdir()
    manifest = {
        "id": plugin_id,
        "name": "Fake Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "minimum_kernel_version": "0.0.0",
        "entry_point": entry_point,
    }
    (plugin_dir / "plugin_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return plugin_dir


_FAKE_ENTRY_POINT = "tests.plugin_discovery.test_discovery:_FakePlugin"
_MISMATCHED_ENTRY_POINT = "tests.plugin_discovery.test_discovery:_MismatchedIdPlugin"


def test_scan_finds_directories_containing_a_manifest_file(tmp_path: Path) -> None:
    _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT)
    _write_plugin_dir(tmp_path, "beta", entry_point=_FAKE_ENTRY_POINT, plugin_id="fake2")
    (tmp_path / "not_a_plugin").mkdir()  # no manifest file -- must be skipped
    (tmp_path / "stray_file.txt").write_text("x", encoding="utf-8")

    discovery = PluginDiscovery()
    found = discovery.scan(tmp_path)

    assert [p.name for p in found] == ["alpha", "beta"]


def test_scan_on_a_non_directory_raises() -> None:
    discovery = PluginDiscovery()

    with pytest.raises(PluginDiscoveryError):
        discovery.scan("this/path/does/not/exist")


def test_scan_on_an_empty_directory_returns_empty_tuple(tmp_path: Path) -> None:
    discovery = PluginDiscovery()

    assert discovery.scan(tmp_path) == ()


def test_read_manifest_delegates_to_the_manifest_filename(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT)
    discovery = PluginDiscovery()

    manifest, entry_point = discovery.read_manifest(plugin_dir)

    assert manifest.id == "fake"
    assert entry_point == _FAKE_ENTRY_POINT


def test_read_manifest_missing_file_raises(tmp_path: Path) -> None:
    (tmp_path / "empty_dir").mkdir()
    discovery = PluginDiscovery()

    with pytest.raises(ManifestNotFoundError):
        discovery.read_manifest(tmp_path / "empty_dir")


def test_load_constructs_the_plugin_without_registering(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT)
    discovery = PluginDiscovery(PluginLoader(kernel_version="1.0.0"))

    plugin = discovery.load(plugin_dir)

    assert isinstance(plugin, _FakePlugin)
    assert plugin.metadata.id == "fake"


def test_load_with_unresolvable_entry_point_raises_entry_point_error(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(tmp_path, "alpha", entry_point="nonexistent_module:NoSuchClass")
    discovery = PluginDiscovery()

    with pytest.raises(EntryPointError):
        discovery.load(plugin_dir)


def test_load_with_id_mismatch_raises_plugin_load_error(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(
        tmp_path, "alpha", entry_point=_MISMATCHED_ENTRY_POINT, plugin_id="fake"
    )
    discovery = PluginDiscovery()

    with pytest.raises(PluginLoadError):
        discovery.load(plugin_dir)


def test_load_with_incompatible_kernel_version_raises_plugin_load_error(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT)
    plugin_dir.joinpath("plugin_manifest.json").write_text(
        json.dumps(
            {
                "id": "fake",
                "name": "Fake Plugin",
                "version": "1.0.0",
                "author": "Test Author",
                "minimum_kernel_version": "999.0.0",
                "entry_point": _FAKE_ENTRY_POINT,
            }
        ),
        encoding="utf-8",
    )
    discovery = PluginDiscovery(PluginLoader(kernel_version="1.0.0"))

    with pytest.raises(PluginLoadError):
        discovery.load(plugin_dir)


def test_discover_and_register_loads_and_registers_every_plugin(tmp_path: Path) -> None:
    _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT, plugin_id="fake")
    registry = PluginRegistry()
    discovery = PluginDiscovery(PluginLoader(kernel_version="1.0.0"))

    discovered = discovery.discover_and_register(tmp_path, registry)

    assert [p.metadata.id for p in discovered] == ["fake"]
    assert registry.lookup("fake") is discovered[0]


def test_discover_and_register_on_empty_root_returns_empty_tuple(tmp_path: Path) -> None:
    registry = PluginRegistry()
    discovery = PluginDiscovery()

    discovered = discovery.discover_and_register(tmp_path, registry)

    assert discovered == ()
    assert registry.enumerate() == ()


def test_discover_and_register_fails_fast_and_keeps_earlier_registrations(tmp_path: Path) -> None:
    """Two plugin directories, sorted so the first (valid) is processed
    before the second (unresolvable) -- the first remains registered
    after the second's failure aborts discovery.
    """
    _write_plugin_dir(tmp_path, "a_first", entry_point=_FAKE_ENTRY_POINT, plugin_id="fake")
    _write_plugin_dir(tmp_path, "b_second", entry_point="nonexistent_module:NoSuchClass")
    registry = PluginRegistry()
    discovery = PluginDiscovery(PluginLoader(kernel_version="1.0.0"))

    with pytest.raises(EntryPointError):
        discovery.discover_and_register(tmp_path, registry)

    assert registry.exists("fake") is True


def test_discover_and_register_raises_on_duplicate_plugin_id(tmp_path: Path) -> None:
    _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT, plugin_id="fake")
    registry = PluginRegistry()
    registry.register(_FakePlugin())
    discovery = PluginDiscovery(PluginLoader(kernel_version="1.0.0"))

    with pytest.raises(PluginRegistrationError):
        discovery.discover_and_register(tmp_path, registry)


def test_custom_manifest_filename_is_respected(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "alpha"
    plugin_dir.mkdir()
    manifest = {
        "id": "fake",
        "name": "Fake Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "entry_point": _FAKE_ENTRY_POINT,
    }
    (plugin_dir / "custom.json").write_text(json.dumps(manifest), encoding="utf-8")
    discovery = PluginDiscovery(manifest_filename="custom.json")

    found = discovery.scan(tmp_path)

    assert found == (plugin_dir,)


def test_default_loader_uses_the_installed_kernel_version(tmp_path: Path) -> None:
    plugin_dir = _write_plugin_dir(tmp_path, "alpha", entry_point=_FAKE_ENTRY_POINT)
    plugin_dir.joinpath("plugin_manifest.json").write_text(
        json.dumps(
            {
                "id": "fake",
                "name": "Fake Plugin",
                "version": "1.0.0",
                "author": "Test Author",
                "minimum_kernel_version": __version__,
                "entry_point": _FAKE_ENTRY_POINT,
            }
        ),
        encoding="utf-8",
    )
    discovery = PluginDiscovery()

    plugin = discovery.load(plugin_dir)

    assert isinstance(plugin, _FakePlugin)
