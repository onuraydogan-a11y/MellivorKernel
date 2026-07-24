"""A registry of plugin instances, keyed by plugin id."""

from __future__ import annotations

from mellivor_kernel.plugins.base import Plugin
from mellivor_kernel.plugins.exceptions import PluginRegistrationError
from mellivor_kernel.plugins.metadata import PluginMetadata


class PluginRegistry:
    """A registry of :class:`Plugin` instances, keyed by each plugin's own
    `metadata.id`.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance under its own metadata id.

        Args:
            plugin: The plugin instance to register.

        Raises:
            PluginRegistrationError: If a plugin is already registered
                under `plugin.metadata.id`.
        """
        plugin_id = plugin.metadata.id
        if plugin_id in self._plugins:
            raise PluginRegistrationError(f"Plugin {plugin_id!r} is already registered.")
        self._plugins[plugin_id] = plugin

    def unregister(self, plugin_id: str) -> None:
        """Remove a registered plugin.

        Args:
            plugin_id: The id of the plugin to remove.

        Raises:
            PluginRegistrationError: If no plugin is registered under
                `plugin_id`.
        """
        try:
            del self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginRegistrationError(f"Plugin {plugin_id!r} is not registered.") from exc

    def lookup(self, plugin_id: str) -> Plugin:
        """Resolve a registered plugin by id.

        Args:
            plugin_id: The id of the plugin to look up.

        Returns:
            The registered plugin instance.

        Raises:
            PluginRegistrationError: If no plugin is registered under
                `plugin_id`.
        """
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginRegistrationError(f"Plugin {plugin_id!r} is not registered.") from exc

    def exists(self, plugin_id: str) -> bool:
        """Return whether a plugin is registered under `plugin_id`.

        Args:
            plugin_id: The id to check.

        Returns:
            `True` if a plugin was registered under `plugin_id` via
            `register`, `False` otherwise.
        """
        return plugin_id in self._plugins

    def enumerate(self) -> tuple[PluginMetadata, ...]:
        """Return metadata for every currently registered plugin.

        Returns:
            A tuple of `PluginMetadata`, one per registered plugin, in
            registration order.
        """
        return tuple(plugin.metadata for plugin in self._plugins.values())
