"""Tests for mellivor_kernel.plugins.registry."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginMetadata,
    PluginRegistrationError,
    PluginRegistry,
)


class _FakePlugin(Plugin):
    def __init__(self, plugin_id: str) -> None:
        self._id = plugin_id

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id=self._id, name=self._id.title(), version="1.0.0", description="")

    def initialize(self, context: PluginContext) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass


def test_register_and_lookup() -> None:
    registry = PluginRegistry()
    plugin = _FakePlugin("alpha")

    registry.register(plugin)

    assert registry.lookup("alpha") is plugin


def test_register_twice_raises() -> None:
    registry = PluginRegistry()
    registry.register(_FakePlugin("alpha"))

    with pytest.raises(PluginRegistrationError):
        registry.register(_FakePlugin("alpha"))


def test_lookup_unregistered_raises() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginRegistrationError):
        registry.lookup("missing")


def test_exists() -> None:
    registry = PluginRegistry()
    assert registry.exists("alpha") is False

    registry.register(_FakePlugin("alpha"))

    assert registry.exists("alpha") is True


def test_unregister_removes_a_plugin() -> None:
    registry = PluginRegistry()
    registry.register(_FakePlugin("alpha"))

    registry.unregister("alpha")

    assert registry.exists("alpha") is False


def test_unregister_unknown_plugin_raises() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginRegistrationError):
        registry.unregister("missing")


def test_unregister_then_register_again_succeeds() -> None:
    registry = PluginRegistry()
    registry.register(_FakePlugin("alpha"))
    registry.unregister("alpha")

    registry.register(_FakePlugin("alpha"))  # must not raise

    assert registry.exists("alpha") is True


def test_enumerate_returns_metadata_in_registration_order() -> None:
    registry = PluginRegistry()
    registry.register(_FakePlugin("alpha"))
    registry.register(_FakePlugin("beta"))

    enumerated = registry.enumerate()

    assert [metadata.id for metadata in enumerated] == ["alpha", "beta"]
    assert all(isinstance(metadata, PluginMetadata) for metadata in enumerated)


def test_enumerate_on_an_empty_registry_returns_an_empty_tuple() -> None:
    registry = PluginRegistry()

    assert registry.enumerate() == ()
