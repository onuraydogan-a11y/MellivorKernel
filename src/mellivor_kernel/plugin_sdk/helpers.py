"""Registration helpers: one-call convenience functions for constructing
plugin manifests, metadata, and capabilities.

None of these register anything into a `PluginRegistry` -- they only
construct value objects. Registering a built `Plugin` instance remains
the caller's own explicit responsibility.
"""

from __future__ import annotations

from collections.abc import Iterable

from mellivor_kernel.plugins import PluginCapability, PluginManifest, PluginMetadata


def create_capability(name: str, description: str = "") -> PluginCapability:
    """Construct a `PluginCapability`.

    Args:
        name: The capability's name.
        description: A human-readable description.

    Returns:
        The constructed capability.

    Raises:
        PluginValidationError: If `name` is blank -- raised by
            `PluginCapability.__post_init__` itself.
    """
    return PluginCapability(name=name, description=description)


def create_manifest(
    *,
    id: str,
    name: str,
    version: str,
    author: str,
    description: str = "",
    capabilities: Iterable[PluginCapability] = (),
    minimum_kernel_version: str = "0.0.0",
) -> PluginManifest:
    """Construct a `PluginManifest` in one call, without a `PluginBuilder`.

    Args:
        id: A short, unique identifier for the plugin.
        name: A human-readable name.
        version: The plugin's own version string (`MAJOR.MINOR.PATCH`).
        author: The plugin's author or owning team.
        description: A human-readable description of what the plugin does.
        capabilities: The capabilities this plugin declares it provides.
        minimum_kernel_version: The lowest compatible kernel version.

    Returns:
        The constructed manifest.

    Raises:
        PluginValidationError: If any field is invalid -- raised by
            `PluginManifest.__post_init__` itself.
    """
    return PluginManifest(
        id=id,
        name=name,
        version=version,
        description=description,
        author=author,
        capabilities=frozenset(capabilities),
        minimum_kernel_version=minimum_kernel_version,
    )


def create_metadata(
    *,
    id: str,
    name: str,
    version: str,
    description: str = "",
    capabilities: Iterable[PluginCapability] = (),
) -> PluginMetadata:
    """Construct a `PluginMetadata` in one call, without a `PluginBuilder`.

    Args:
        id: A short, unique identifier for the plugin.
        name: A human-readable name.
        version: The plugin's own version string.
        description: A human-readable description of what the plugin does.
        capabilities: The capabilities this plugin instance declares.

    Returns:
        The constructed metadata.

    Raises:
        PluginValidationError: If any field is invalid -- raised by
            `PluginMetadata.__post_init__` itself.
    """
    return PluginMetadata(
        id=id,
        name=name,
        version=version,
        description=description,
        capabilities=frozenset(capabilities),
    )
