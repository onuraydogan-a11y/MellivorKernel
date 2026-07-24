"""PluginDiscovery: discovers plugins from a filesystem location and loads
and registers them through the existing Plugin Runtime.
"""

from __future__ import annotations

from pathlib import Path

from mellivor_kernel.plugin_discovery.entry_point import resolve_entry_point
from mellivor_kernel.plugin_discovery.exceptions import PluginDiscoveryError
from mellivor_kernel.plugin_discovery.manifest_file import read_manifest_file
from mellivor_kernel.plugins import Plugin, PluginLoader, PluginManifest, PluginRegistry

DEFAULT_MANIFEST_FILENAME = "plugin_manifest.json"


class PluginDiscovery:
    """Discovers plugins from a filesystem location and loads/registers
    them through the existing Plugin Runtime (`PluginLoader`,
    `PluginRegistry`) -- introduces no new loading, validation, or
    registration logic of its own.

    Discovery convention: `root` contains one subdirectory per plugin,
    each containing a manifest file (`manifest_filename`, default
    `"plugin_manifest.json"`) -- the same `PluginManifest` fields (`id`,
    `name`, `version`, `description`, `author`, `capabilities`,
    `minimum_kernel_version`) plus a discovery-only `entry_point` string
    (`"module.path:AttributeName"`) naming the zero-argument callable that
    constructs the `Plugin` instance.

    No marketplace, remote plugins, sandboxing, hot reload, signature
    verification, or package installation -- a discovered plugin's code is
    imported and executed with the same trust as any other import in the
    running process.
    """

    def __init__(
        self,
        loader: PluginLoader | None = None,
        *,
        manifest_filename: str = DEFAULT_MANIFEST_FILENAME,
    ) -> None:
        """Initialize the discoverer.

        Args:
            loader: The loader used to validate compatibility and
                instantiate each discovered plugin. Defaults to a new
                `PluginLoader()` (kernel version taken from the installed
                package).
            manifest_filename: The filename identifying a plugin
                directory, checked as an immediate child of each
                candidate directory under `root`.
        """
        self._loader = loader if loader is not None else PluginLoader()
        self._manifest_filename = manifest_filename

    def scan(self, root: Path | str) -> tuple[Path, ...]:
        """Return every immediate subdirectory of `root` containing a
        manifest file.

        Args:
            root: The filesystem location to scan.

        Returns:
            The matching subdirectories, sorted by name for determinism.

        Raises:
            PluginDiscoveryError: If `root` is not a directory.
        """
        root_path = Path(root)
        if not root_path.is_dir():
            raise PluginDiscoveryError(f"{root_path} is not a directory.")
        return tuple(
            child
            for child in sorted(root_path.iterdir())
            if child.is_dir() and (child / self._manifest_filename).is_file()
        )

    def read_manifest(self, plugin_dir: Path | str) -> tuple[PluginManifest, str]:
        """Read and parse the manifest file in `plugin_dir`.

        Args:
            plugin_dir: The plugin's directory.

        Returns:
            A `(manifest, entry_point)` pair.

        Raises:
            ManifestNotFoundError: If `plugin_dir` has no manifest file.
            ManifestParseError: If the manifest file is malformed.
            PluginValidationError: If a present field's value is invalid.
        """
        return read_manifest_file(Path(plugin_dir) / self._manifest_filename)

    def load(self, plugin_dir: Path | str) -> Plugin:
        """Read `plugin_dir`'s manifest and load the plugin it describes.

        Does not register the plugin into any `PluginRegistry`.

        Args:
            plugin_dir: The plugin's directory.

        Returns:
            The constructed, loaded plugin instance.

        Raises:
            ManifestNotFoundError: If `plugin_dir` has no manifest file.
            ManifestParseError: If the manifest file is malformed.
            EntryPointError: If the entry point cannot be resolved.
            PluginValidationError: If a manifest field's value is invalid.
            PluginLoadError: If the manifest is incompatible with the
                running kernel, the entry point fails to construct a
                plugin, or the constructed plugin's id does not match the
                manifest's -- raised by `PluginLoader.load()` itself.
        """
        manifest, entry_point = self.read_manifest(plugin_dir)
        factory = resolve_entry_point(entry_point)
        return self._loader.load(manifest, factory)

    def discover_and_register(
        self, root: Path | str, registry: PluginRegistry
    ) -> tuple[Plugin, ...]:
        """Scan `root`, load every plugin found, and register each into
        `registry`.

        Fails fast: the first error raised by `scan()`/`load()`/
        `registry.register()` aborts discovery immediately. Plugins
        already registered before that point remain registered -- this
        method never rolls back a partially completed discovery.

        Args:
            root: The filesystem location to discover plugins from.
            registry: The registry each discovered plugin is registered
                into, in discovery order.

        Returns:
            The discovered plugins, in discovery order.

        Raises:
            PluginDiscoveryError: If `root` is not a directory.
            ManifestNotFoundError: If a candidate directory has no
                manifest file.
            ManifestParseError: If a manifest file is malformed.
            EntryPointError: If an entry point cannot be resolved.
            PluginValidationError: If a manifest field's value is invalid.
            PluginLoadError: If a manifest is incompatible with the
                running kernel, its entry point fails to construct a
                plugin, or the constructed plugin's id does not match.
            PluginRegistrationError: If a discovered plugin's id is
                already registered.
        """
        discovered: list[Plugin] = []
        for plugin_dir in self.scan(root):
            plugin = self.load(plugin_dir)
            registry.register(plugin)
            discovered.append(plugin)
        return tuple(discovered)
