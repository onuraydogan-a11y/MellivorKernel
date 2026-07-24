"""Plugin: the contract every kernel plugin must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mellivor_kernel.plugins.context import PluginContext
from mellivor_kernel.plugins.metadata import PluginMetadata


class Plugin(ABC):
    """The contract every kernel plugin must implement.

    A plugin is a consumer-supplied extension point (ADR-0004): the
    kernel ships no built-in plugins. Concrete plugins declare their
    identity through `metadata` and implement the four lifecycle methods
    below; nothing else is required. `PluginLifecycle` is responsible for
    calling these methods in a valid order -- `Plugin` itself enforces
    nothing about call sequencing.
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """A snapshot of this plugin's identity and declared capabilities."""
        ...

    @abstractmethod
    def initialize(self, context: PluginContext) -> None:
        """Prepare this plugin to run, given its kernel-scoped context.

        Called exactly once, before the first `start()`. A plugin that
        needs kernel services (configuration, logging, the service
        container) resolves them here and retains what it needs.

        Args:
            context: The kernel-scoped context this plugin runs with.
        """
        ...

    @abstractmethod
    def start(self) -> None:
        """Begin this plugin's active behavior.

        Callable only after `initialize()`, or again after `stop()` (a
        plugin may be restarted).
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """End this plugin's active behavior without releasing its resources.

        Callable only while running; a stopped plugin may be `start()`ed
        again.
        """
        ...

    @abstractmethod
    def dispose(self) -> None:
        """Release this plugin's resources permanently.

        Terminal: a disposed plugin is never started again.
        """
        ...
