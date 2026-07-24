"""Plugin runtime exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class PluginError(KernelError):
    """Base class for all errors raised by the plugin runtime."""


class PluginValidationError(PluginError):
    """Raised when a `PluginCapability`, `PluginMetadata`, or
    `PluginManifest` value is invalid.
    """


class PluginRegistrationError(PluginError):
    """Raised when a plugin cannot be registered with, or resolved from, a
    `PluginRegistry`.
    """


class PluginLoadError(PluginError):
    """Raised when a plugin manifest is incompatible with the running
    kernel, or when `PluginLoader` fails to instantiate the plugin it
    describes.
    """


class PluginLifecycleError(PluginError):
    """Raised when a `PluginLifecycle` transition is called out of order,
    or the underlying plugin raises during one.
    """
