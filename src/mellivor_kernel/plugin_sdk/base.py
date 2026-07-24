"""BasePlugin: a convenience base implementation of the Plugin contract."""

from __future__ import annotations

from abc import abstractmethod

from mellivor_kernel.plugins import Plugin, PluginContext, PluginMetadata


class BasePlugin(Plugin):
    """A convenience base implementation of `Plugin`.

    Supplies no-op default lifecycle methods so a concrete plugin
    overrides only the ones it actually needs. `metadata` remains
    abstract -- every plugin must declare its own identity; there is no
    sensible default for it.
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """A snapshot of this plugin's identity and declared capabilities."""
        ...

    def initialize(self, context: PluginContext) -> None:
        """Default no-op. Override to perform setup with `context`."""

    def start(self) -> None:
        """Default no-op. Override to begin active behavior."""

    def stop(self) -> None:
        """Default no-op. Override to end active behavior."""

    def dispose(self) -> None:
        """Default no-op. Override to release resources."""
