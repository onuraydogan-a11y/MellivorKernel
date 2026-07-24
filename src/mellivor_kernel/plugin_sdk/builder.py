"""PluginBuilder: a fluent builder simplifying PluginManifest/PluginMetadata
construction.
"""

from __future__ import annotations

from mellivor_kernel.plugins import PluginCapability, PluginManifest, PluginMetadata


class PluginBuilder:
    """A fluent builder simplifying `PluginManifest`/`PluginMetadata`
    construction.

    Accumulates field values via chained `with_*` calls, then produces
    either a `PluginManifest` (via `build_manifest()`) or a
    `PluginMetadata` (via `build_metadata()`) from the same accumulated
    state. Performs no validation of its own: every field is validated
    only when the underlying constructor is actually called, so
    `PluginValidationError` is raised by, and only by, the Plugin Runtime
    Foundation's own contracts (ADR-0014) -- this builder never
    duplicates that logic.
    """

    def __init__(self) -> None:
        """Initialize an empty builder."""
        self._id = ""
        self._name = ""
        self._version = ""
        self._author = ""
        self._description = ""
        self._capabilities: frozenset[PluginCapability] = frozenset()
        self._minimum_kernel_version = "0.0.0"

    def with_id(self, value: str) -> PluginBuilder:
        """Set the plugin id.

        Returns:
            This builder, for chaining.
        """
        self._id = value
        return self

    def with_name(self, value: str) -> PluginBuilder:
        """Set the plugin's human-readable name.

        Returns:
            This builder, for chaining.
        """
        self._name = value
        return self

    def with_version(self, value: str) -> PluginBuilder:
        """Set the plugin's own version string.

        Returns:
            This builder, for chaining.
        """
        self._version = value
        return self

    def with_author(self, value: str) -> PluginBuilder:
        """Set the plugin's author or owning team.

        Only consumed by `build_manifest()` -- `PluginMetadata` has no
        `author` field.

        Returns:
            This builder, for chaining.
        """
        self._author = value
        return self

    def with_description(self, value: str) -> PluginBuilder:
        """Set the plugin's human-readable description.

        Returns:
            This builder, for chaining.
        """
        self._description = value
        return self

    def with_capability(self, name: str, description: str = "") -> PluginBuilder:
        """Add one capability to the accumulated set.

        Returns:
            This builder, for chaining.

        Raises:
            PluginValidationError: If `name` is blank -- raised by
                `PluginCapability.__post_init__` itself.
        """
        self._capabilities = self._capabilities | frozenset(
            {PluginCapability(name=name, description=description)}
        )
        return self

    def with_capabilities(self, *capabilities: PluginCapability) -> PluginBuilder:
        """Replace the accumulated capability set entirely.

        Returns:
            This builder, for chaining.
        """
        self._capabilities = frozenset(capabilities)
        return self

    def with_minimum_kernel_version(self, value: str) -> PluginBuilder:
        """Set the minimum compatible kernel version.

        Only consumed by `build_manifest()` -- `PluginMetadata` has no
        `minimum_kernel_version` field.

        Returns:
            This builder, for chaining.
        """
        self._minimum_kernel_version = value
        return self

    def build_manifest(self) -> PluginManifest:
        """Construct a `PluginManifest` from the accumulated fields.

        Returns:
            The constructed manifest.

        Raises:
            PluginValidationError: If any accumulated field is invalid --
                raised by `PluginManifest.__post_init__` itself, not by
                this builder.
        """
        return PluginManifest(
            id=self._id,
            name=self._name,
            version=self._version,
            description=self._description,
            author=self._author,
            capabilities=self._capabilities,
            minimum_kernel_version=self._minimum_kernel_version,
        )

    def build_metadata(self) -> PluginMetadata:
        """Construct a `PluginMetadata` from the accumulated fields.

        `author` and `minimum_kernel_version`, even if set, are ignored --
        `PluginMetadata` has no corresponding fields.

        Returns:
            The constructed metadata.

        Raises:
            PluginValidationError: If any accumulated field is invalid --
                raised by `PluginMetadata.__post_init__` itself, not by
                this builder.
        """
        return PluginMetadata(
            id=self._id,
            name=self._name,
            version=self._version,
            description=self._description,
            capabilities=self._capabilities,
        )
