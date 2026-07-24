"""PluginMetadata: a snapshot of a loaded plugin's self-declared identity."""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.plugins.capability import PluginCapability
from mellivor_kernel.plugins.exceptions import PluginValidationError


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """A snapshot of a plugin instance's static, self-declared identity.

    Returned by `Plugin.metadata` -- the same role `tools.ToolMetadata`
    plays for `BaseTool.metadata()`, and what `PluginRegistry.enumerate()`
    returns rather than live plugin instances.

    Attributes:
        id: A short, unique identifier for the plugin, matching the
            `PluginManifest.id` it was loaded from.
        name: A human-readable name.
        version: The plugin's own version string.
        description: A human-readable description of what the plugin does.
        capabilities: The capabilities this plugin instance declares.
    """

    id: str
    name: str
    version: str
    description: str
    capabilities: frozenset[PluginCapability] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate field values.

        Raises:
            PluginValidationError: If `id`, `name`, or `version` is blank.
        """
        if not self.id.strip():
            raise PluginValidationError("PluginMetadata.id must not be blank.")
        if not self.name.strip():
            raise PluginValidationError("PluginMetadata.name must not be blank.")
        if not self.version.strip():
            raise PluginValidationError("PluginMetadata.version must not be blank.")
