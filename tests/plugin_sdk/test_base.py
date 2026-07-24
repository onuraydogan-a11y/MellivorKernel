"""Tests for mellivor_kernel.plugin_sdk.base."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugin_sdk import BasePlugin
from mellivor_kernel.plugins import Plugin, PluginContext, PluginMetadata


class _FakeSettings:
    log_level = "INFO"


def _make_context() -> PluginContext:
    settings = _FakeSettings()
    return PluginContext(
        configuration=settings,
        logger=get_logger("test_base_plugin"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


class _MinimalPlugin(BasePlugin):
    """Only overrides `metadata` -- proves the four lifecycle defaults work."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id="minimal", name="Minimal", version="1.0.0", description="")


class _PartiallyOverridingPlugin(BasePlugin):
    """Overrides only `start()`, leaving the other three defaults in place."""

    def __init__(self) -> None:
        self.started = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(id="partial", name="Partial", version="1.0.0", description="")

    def start(self) -> None:
        self.started = True


def test_base_plugin_is_a_plugin() -> None:
    plugin = _MinimalPlugin()

    assert isinstance(plugin, Plugin)


def test_base_plugin_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BasePlugin()  # type: ignore[abstract]


def test_default_lifecycle_methods_are_no_ops() -> None:
    plugin = _MinimalPlugin()
    context = _make_context()

    plugin.initialize(context)  # must not raise
    plugin.start()  # must not raise
    plugin.stop()  # must not raise
    plugin.dispose()  # must not raise


def test_overriding_only_one_lifecycle_method_leaves_the_others_as_no_ops() -> None:
    plugin = _PartiallyOverridingPlugin()
    context = _make_context()

    plugin.initialize(context)
    plugin.start()
    plugin.stop()
    plugin.dispose()

    assert plugin.started is True


def test_metadata_remains_abstract() -> None:
    class _IncompletePlugin(BasePlugin):
        pass  # metadata deliberately left unimplemented

    with pytest.raises(TypeError):
        _IncompletePlugin()  # type: ignore[abstract]
