"""PluginLoader: validates a manifest's kernel-version compatibility and
instantiates the plugin it describes.
"""

from __future__ import annotations

from collections.abc import Callable

from mellivor_kernel.plugins.base import Plugin
from mellivor_kernel.plugins.exceptions import PluginLoadError
from mellivor_kernel.plugins.manifest import PluginManifest
from mellivor_kernel.plugins.versioning import parse_version
from mellivor_kernel.version import __version__


class PluginLoader:
    """Validates and instantiates plugins from an explicit
    `PluginManifest` and constructor.

    No filesystem or entry-point discovery at this sprint's scope -- a
    caller supplies both the manifest and a zero-argument constructor
    directly, the same explicit-registration shape
    `providers.ProviderFactory` uses.
    """

    def __init__(self, *, kernel_version: str | None = None) -> None:
        """Initialize the loader.

        Args:
            kernel_version: The running kernel's version, compared
                against each manifest's `minimum_kernel_version`.
                Defaults to the installed `mellivor_kernel` package
                version.
        """
        self._kernel_version = kernel_version if kernel_version is not None else __version__

    def load(self, manifest: PluginManifest, factory: Callable[[], Plugin]) -> Plugin:
        """Validate `manifest`, then instantiate the plugin it describes.

        Args:
            manifest: The manifest declaring the plugin's identity and
                minimum kernel version.
            factory: A zero-argument callable that constructs the
                `Plugin` instance `manifest` describes.

        Returns:
            The constructed plugin instance.

        Raises:
            PluginLoadError: If `manifest.minimum_kernel_version` is
                newer than the running kernel, if `factory` raises, or if
                the constructed plugin's own `metadata.id` does not match
                `manifest.id`.
        """
        self._check_compatibility(manifest)

        try:
            plugin = factory()
        except Exception as exc:
            raise PluginLoadError(f"Plugin {manifest.id!r} failed to instantiate: {exc}") from exc

        if plugin.metadata.id != manifest.id:
            raise PluginLoadError(
                f"Plugin instance id {plugin.metadata.id!r} does not match "
                f"the manifest it was loaded from ({manifest.id!r})."
            )
        return plugin

    def _check_compatibility(self, manifest: PluginManifest) -> None:
        """Raise unless the running kernel satisfies `manifest.minimum_kernel_version`."""
        required = parse_version(
            manifest.minimum_kernel_version, field_name="PluginManifest.minimum_kernel_version"
        )
        running = parse_version(self._kernel_version, field_name="kernel_version")
        if required > running:
            raise PluginLoadError(
                f"Plugin {manifest.id!r} requires kernel >= "
                f"{manifest.minimum_kernel_version}, but the running kernel is "
                f"{self._kernel_version}."
            )
