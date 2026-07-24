"""Tests for mellivor_kernel.plugins.base."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugins import Plugin, PluginContext, PluginMetadata


class _FakeSettings:
    log_level = "INFO"


class _RecordingPlugin(Plugin):
    """A minimal concrete `Plugin`, recording each lifecycle call it receives."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="recording", name="Recording Plugin", version="1.0.0", description=""
        )

    def initialize(self, context: PluginContext) -> None:
        self.calls.append("initialize")

    def start(self) -> None:
        self.calls.append("start")

    def stop(self) -> None:
        self.calls.append("stop")

    def dispose(self) -> None:
        self.calls.append("dispose")


def _make_context() -> PluginContext:
    settings = _FakeSettings()
    return PluginContext(
        configuration=settings,
        logger=get_logger("test_plugin_base"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_plugin_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Plugin()  # type: ignore[abstract]


def test_concrete_plugin_exposes_metadata() -> None:
    plugin = _RecordingPlugin()

    assert plugin.metadata.id == "recording"
    assert plugin.metadata.name == "Recording Plugin"


def test_concrete_plugin_lifecycle_methods_are_callable() -> None:
    plugin = _RecordingPlugin()
    context = _make_context()

    plugin.initialize(context)
    plugin.start()
    plugin.stop()
    plugin.dispose()

    assert plugin.calls == ["initialize", "start", "stop", "dispose"]


def test_incomplete_plugin_subclass_cannot_be_instantiated() -> None:
    class _IncompletePlugin(Plugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                id="incomplete", name="Incomplete", version="1.0.0", description=""
            )

        # initialize/start/stop/dispose deliberately left unimplemented.

    with pytest.raises(TypeError):
        _IncompletePlugin()  # type: ignore[abstract]
