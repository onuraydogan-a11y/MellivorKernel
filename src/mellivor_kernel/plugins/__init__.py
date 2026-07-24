"""Public API of the kernel's plugin runtime foundation.

Plugin loading is a named kernel responsibility (ADR-0002) providing the
extension point through which a consuming application adds behavior the
kernel does not natively provide (ADR-0004) -- never by forking or
monkey-patching kernel internals. This sprint ships the runtime
*foundation* only: contracts, an immutable manifest model, a registry, a
loader, and lifecycle state management -- see ADR-0014. No built-in
plugins ship with the kernel, and no filesystem or entry-point discovery
is implemented yet; a consumer supplies an explicit `PluginManifest` and
constructor.
"""

from __future__ import annotations

from mellivor_kernel.plugins.base import Plugin
from mellivor_kernel.plugins.capability import PluginCapability
from mellivor_kernel.plugins.context import PluginContext
from mellivor_kernel.plugins.exceptions import (
    PluginError,
    PluginLifecycleError,
    PluginLoadError,
    PluginRegistrationError,
    PluginValidationError,
)
from mellivor_kernel.plugins.lifecycle import PluginLifecycle, PluginLifecycleState
from mellivor_kernel.plugins.loader import PluginLoader
from mellivor_kernel.plugins.manifest import PluginManifest
from mellivor_kernel.plugins.metadata import PluginMetadata
from mellivor_kernel.plugins.registry import PluginRegistry

__all__ = [
    "Plugin",
    "PluginCapability",
    "PluginContext",
    "PluginError",
    "PluginLifecycle",
    "PluginLifecycleError",
    "PluginLifecycleState",
    "PluginLoadError",
    "PluginLoader",
    "PluginManifest",
    "PluginMetadata",
    "PluginRegistrationError",
    "PluginRegistry",
    "PluginValidationError",
]
