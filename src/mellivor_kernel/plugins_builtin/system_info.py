"""SystemInfoPlugin: the kernel's first built-in plugin, exposing
read-only kernel information.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass

from mellivor_kernel.core import HealthStatus, ServiceRegistrationError
from mellivor_kernel.plugin_sdk import BasePlugin
from mellivor_kernel.plugins import (
    PluginCapability,
    PluginContext,
    PluginLifecycleError,
    PluginMetadata,
    PluginRegistry,
)
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.version import __version__


@dataclass(frozen=True, slots=True)
class SystemInfoSnapshot:
    """A point-in-time, read-only snapshot of kernel information.

    Attributes:
        kernel_version: The installed `mellivor_kernel` package version.
        build_info: A human-readable description of the running Python
            interpreter and platform.
        available_capabilities: The union of `PluginCapability.name`
            across every plugin known to this plugin's `PluginRegistry`
            (or, if none was supplied, just this plugin's own declared
            capabilities).
        registered_providers: The names of every provider registered in
            the resolved `ProviderRegistry`, or an empty tuple if none is
            available.
        registered_tools: The ids of every tool registered in the
            resolved `ToolRegistry`, or an empty tuple if none is
            available.
        runtime_health: The kernel runtime's current `HealthStatus`.
    """

    kernel_version: str
    build_info: str
    available_capabilities: frozenset[str]
    registered_providers: tuple[str, ...]
    registered_tools: tuple[str, ...]
    runtime_health: HealthStatus


class SystemInfoPlugin(BasePlugin):
    """The kernel's first built-in plugin: exposes read-only kernel
    information (version, build info, available capabilities,
    registered providers/tools, and runtime health).

    Demonstrates `BasePlugin`'s "override only when necessary" design
    (ADR-0015): only `metadata` and `initialize()` are overridden --
    `start()`, `stop()`, and `dispose()` remain the inherited no-ops,
    since a read-only reporting plugin has no active behavior to begin,
    end, or resources to release.

    Performs no mutation and no configuration change -- every method is
    a pure read/report operation. Not registered automatically; a caller
    still registers a constructed instance into a `PluginRegistry`
    explicitly (ADR-0014/ADR-0015).
    """

    def __init__(self, *, plugin_registry: PluginRegistry | None = None) -> None:
        """Initialize the plugin.

        Args:
            plugin_registry: An optional registry to read
                `available_capabilities` from (the union of every
                registered plugin's declared capabilities). If omitted,
                `collect()` reports only this plugin's own capabilities.
                Never registered into, only enumerated from.
        """
        self._context: PluginContext | None = None
        self._plugin_registry = plugin_registry

    @property
    def metadata(self) -> PluginMetadata:
        """A snapshot of this plugin's identity and declared capabilities."""
        return PluginMetadata(
            id="system-info",
            name="System Information Plugin",
            version="1.0.0",
            description=(
                "Exposes read-only kernel information: version, build info, "
                "available capabilities, registered providers/tools, and runtime health."
            ),
            capabilities=frozenset(
                {
                    PluginCapability(
                        name="kernel.introspection",
                        description="Read-only kernel and runtime information.",
                    )
                }
            ),
        )

    def initialize(self, context: PluginContext) -> None:
        """Retain `context` for later use by `collect()`.

        Args:
            context: The kernel-scoped context this plugin runs with.
        """
        self._context = context

    def collect(self) -> SystemInfoSnapshot:
        """Collect a fresh `SystemInfoSnapshot`.

        Returns:
            The current system information snapshot.

        Raises:
            PluginLifecycleError: If called before `initialize()`.
        """
        if self._context is None:
            raise PluginLifecycleError("SystemInfoPlugin.collect() was called before initialize().")

        return SystemInfoSnapshot(
            kernel_version=__version__,
            build_info=(
                f"Python {platform.python_version()} on {platform.system()} {platform.release()}"
            ),
            available_capabilities=self._collect_available_capabilities(),
            registered_providers=self._resolve_provider_names(),
            registered_tools=self._resolve_tool_ids(),
            runtime_health=self._context.runtime.health(),
        )

    def _collect_available_capabilities(self) -> frozenset[str]:
        """Return the union of every known plugin's capability names.

        Falls back to this plugin's own capabilities if no
        `PluginRegistry` was supplied at construction.
        """
        if self._plugin_registry is None:
            return frozenset(capability.name for capability in self.metadata.capabilities)
        names: set[str] = set()
        for metadata in self._plugin_registry.enumerate():
            names.update(capability.name for capability in metadata.capabilities)
        return frozenset(names)

    def _resolve_provider_names(self) -> tuple[str, ...]:
        """Return every registered provider's name, or `()` if unavailable."""
        assert self._context is not None
        try:
            registry = self._context.services.resolve(ProviderRegistry)
        except ServiceRegistrationError:
            return ()
        return registry.list_providers()

    def _resolve_tool_ids(self) -> tuple[str, ...]:
        """Return every registered tool's id, or `()` if unavailable."""
        assert self._context is not None
        try:
            registry = self._context.services.resolve(ToolRegistry)
        except ServiceRegistrationError:
            return ()
        return tuple(metadata.id for metadata in registry.enumerate())
