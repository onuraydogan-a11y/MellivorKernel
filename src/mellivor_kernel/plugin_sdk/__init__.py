"""Public API of the Plugin SDK -- the developer-facing toolkit for
building kernel plugins.

The Plugin Runtime Foundation (`mellivor_kernel.plugins`, ADR-0014)
defines the contracts and primitives a plugin is loaded, validated,
registered, and run through. This SDK does not replace or duplicate any
of that -- it only makes it easier to *use*: `PluginBuilder` and the
`create_*`/`is_valid_*` helpers all delegate to the exact same
`PluginManifest`/`PluginMetadata`/`PluginCapability` constructors the
runtime itself validates with, and `BasePlugin` supplies no-op lifecycle
defaults over the same `Plugin` contract -- see ADR-0015.

No plugin discovery, marketplace, sandboxing, or filesystem loading is
implemented here or anywhere else in the kernel yet. Nothing in this
package performs automatic registration; a consumer still registers a
built `Plugin` instance into a `PluginRegistry` explicitly.
"""

from __future__ import annotations

from mellivor_kernel.plugin_sdk.base import BasePlugin
from mellivor_kernel.plugin_sdk.builder import PluginBuilder
from mellivor_kernel.plugin_sdk.helpers import create_capability, create_manifest, create_metadata
from mellivor_kernel.plugin_sdk.validation import (
    is_valid_capability,
    is_valid_manifest,
    is_valid_metadata,
)

__all__ = [
    "BasePlugin",
    "PluginBuilder",
    "create_capability",
    "create_manifest",
    "create_metadata",
    "is_valid_capability",
    "is_valid_manifest",
    "is_valid_metadata",
]
