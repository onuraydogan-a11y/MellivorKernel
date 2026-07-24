"""Validation helpers: convenience predicates delegating entirely to the
Plugin Runtime Foundation's own contracts -- no validation rule is
duplicated here.
"""

from __future__ import annotations

from collections.abc import Iterable

from mellivor_kernel.plugins import (
    PluginCapability,
    PluginManifest,
    PluginMetadata,
    PluginValidationError,
)


def is_valid_capability(name: str, description: str = "") -> bool:
    """Return whether `name`/`description` would construct a valid
    `PluginCapability`.

    Delegates entirely to `PluginCapability.__post_init__` -- no
    validation rule is duplicated here.
    """
    try:
        PluginCapability(name=name, description=description)
    except PluginValidationError:
        return False
    return True


def is_valid_metadata(
    *,
    id: str,
    name: str,
    version: str,
    description: str = "",
    capabilities: Iterable[PluginCapability] = (),
) -> bool:
    """Return whether the given fields would construct a valid
    `PluginMetadata`.

    Delegates entirely to `PluginMetadata.__post_init__` -- no validation
    rule is duplicated here.
    """
    try:
        PluginMetadata(
            id=id,
            name=name,
            version=version,
            description=description,
            capabilities=frozenset(capabilities),
        )
    except PluginValidationError:
        return False
    return True


def is_valid_manifest(
    *,
    id: str,
    name: str,
    version: str,
    author: str,
    description: str = "",
    capabilities: Iterable[PluginCapability] = (),
    minimum_kernel_version: str = "0.0.0",
) -> bool:
    """Return whether the given fields would construct a valid
    `PluginManifest`.

    Delegates entirely to `PluginManifest.__post_init__` -- no validation
    rule is duplicated here.
    """
    try:
        PluginManifest(
            id=id,
            name=name,
            version=version,
            description=description,
            author=author,
            capabilities=frozenset(capabilities),
            minimum_kernel_version=minimum_kernel_version,
        )
    except PluginValidationError:
        return False
    return True
