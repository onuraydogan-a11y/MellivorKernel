"""Public API of the kernel's Plugin Discovery Foundation.

Discovers plugins from a filesystem location, validates their manifests,
and loads/registers them through the existing Plugin Runtime
(`mellivor_kernel.plugins.PluginLoader`/`PluginRegistry`) -- introduces no
new loading, validation, or registration logic of its own; see ADR-0017.

Explicitly out of scope: a plugin marketplace, remote plugins, sandboxing,
hot reload, signature verification, and package installation. A
discovered plugin's code is imported and executed with the same trust as
any other import in the running process.
"""

from __future__ import annotations

from mellivor_kernel.plugin_discovery.discovery import DEFAULT_MANIFEST_FILENAME, PluginDiscovery
from mellivor_kernel.plugin_discovery.exceptions import (
    EntryPointError,
    ManifestNotFoundError,
    ManifestParseError,
    PluginDiscoveryError,
)

__all__ = [
    "DEFAULT_MANIFEST_FILENAME",
    "EntryPointError",
    "ManifestNotFoundError",
    "ManifestParseError",
    "PluginDiscovery",
    "PluginDiscoveryError",
]
