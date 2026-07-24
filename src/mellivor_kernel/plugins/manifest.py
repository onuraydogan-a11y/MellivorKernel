"""PluginManifest: the immutable, load-time declarative descriptor a plugin
is loaded from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.plugins.capability import PluginCapability
from mellivor_kernel.plugins.exceptions import PluginValidationError
from mellivor_kernel.plugins.versioning import parse_version


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """An immutable, validated declaration of a plugin's identity and
    compatibility requirements.

    This is the input to `PluginLoader.load()` -- the "package
    declaration" a plugin is loaded from, as distinct from
    `PluginMetadata`, the runtime snapshot a *loaded* plugin instance
    self-reports. No filesystem or entry-point discovery reads this from
    disk yet (see `PluginLoader`); at this sprint's scope a manifest is
    always constructed explicitly by the caller.

    Attributes:
        id: A short, unique identifier for the plugin.
        name: A human-readable name.
        version: The plugin's own version string (`MAJOR.MINOR.PATCH`).
        description: A human-readable description of what the plugin does.
        author: The plugin's author or owning team.
        capabilities: The capabilities this plugin declares it provides.
        minimum_kernel_version: The lowest kernel `MAJOR.MINOR.PATCH`
            version this plugin is compatible with. Checked against the
            running kernel by `PluginLoader`, not by this dataclass --
            constructing a manifest never requires knowing the current
            kernel version.
    """

    id: str
    name: str
    version: str
    description: str
    author: str
    capabilities: frozenset[PluginCapability] = field(default_factory=frozenset)
    minimum_kernel_version: str = "0.0.0"

    def __post_init__(self) -> None:
        """Validate field values.

        Raises:
            PluginValidationError: If `id`, `name`, or `author` is blank,
                or if `version`/`minimum_kernel_version` is not a
                `MAJOR.MINOR.PATCH` string.
        """
        if not self.id.strip():
            raise PluginValidationError("PluginManifest.id must not be blank.")
        if not self.name.strip():
            raise PluginValidationError("PluginManifest.name must not be blank.")
        if not self.author.strip():
            raise PluginValidationError("PluginManifest.author must not be blank.")
        parse_version(self.version, field_name="PluginManifest.version")
        parse_version(
            self.minimum_kernel_version, field_name="PluginManifest.minimum_kernel_version"
        )
