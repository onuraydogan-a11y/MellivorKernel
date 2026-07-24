"""Plugin discovery exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class PluginDiscoveryError(KernelError):
    """Base class for all errors raised by plugin discovery."""


class ManifestNotFoundError(PluginDiscoveryError):
    """Raised when a candidate plugin directory has no manifest file."""


class ManifestParseError(PluginDiscoveryError):
    """Raised when a manifest file exists but is not valid JSON, is not a
    JSON object, or is missing a required discovery-level field
    (`entry_point`, or any of `PluginManifest`'s required fields).
    """


class EntryPointError(PluginDiscoveryError):
    """Raised when a manifest's `entry_point` string is malformed, or its
    module/attribute cannot be resolved, or the resolved attribute is not
    callable.
    """
