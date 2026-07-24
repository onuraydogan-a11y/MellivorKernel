"""Manifest validation tests for the system-info built-in plugin, built
through the Plugin SDK.
"""

from __future__ import annotations

from typing import TypedDict

import pytest

from mellivor_kernel.plugin_sdk import PluginBuilder, create_manifest, is_valid_manifest
from mellivor_kernel.plugins import PluginManifest, PluginValidationError
from mellivor_kernel.plugins_builtin import SystemInfoPlugin
from mellivor_kernel.version import __version__


class _ManifestFields(TypedDict):
    id: str
    name: str
    version: str
    description: str
    author: str
    minimum_kernel_version: str


def _plugin_manifest_fields() -> _ManifestFields:
    plugin = SystemInfoPlugin()
    return _ManifestFields(
        id=plugin.metadata.id,
        name=plugin.metadata.name,
        version=plugin.metadata.version,
        description=plugin.metadata.description,
        author="Mellivor Kernel",
        minimum_kernel_version=__version__,
    )


def test_manifest_built_via_builder_is_valid() -> None:
    fields = _plugin_manifest_fields()

    manifest = (
        PluginBuilder()
        .with_id(fields["id"])
        .with_name(fields["name"])
        .with_version(fields["version"])
        .with_author(fields["author"])
        .with_description(fields["description"])
        .with_minimum_kernel_version(fields["minimum_kernel_version"])
        .build_manifest()
    )

    assert isinstance(manifest, PluginManifest)
    assert manifest.id == "system-info"
    assert manifest.minimum_kernel_version == __version__


def test_manifest_built_via_create_manifest_is_valid() -> None:
    fields = _plugin_manifest_fields()

    manifest = create_manifest(**fields)

    assert isinstance(manifest, PluginManifest)
    assert manifest.id == "system-info"


def test_manifest_fields_pass_is_valid_manifest() -> None:
    fields = _plugin_manifest_fields()

    assert is_valid_manifest(**fields) is True


def test_manifest_with_blank_id_is_rejected() -> None:
    fields = _plugin_manifest_fields()
    fields["id"] = ""

    assert is_valid_manifest(**fields) is False
    with pytest.raises(PluginValidationError):
        create_manifest(**fields)


def test_manifest_incompatible_with_a_future_kernel_version_is_still_structurally_valid() -> None:
    """A manifest requiring a not-yet-released kernel version is a valid
    `PluginManifest` -- the mismatch is a `PluginLoader` concern (see
    `test_loader.py`), not a manifest-construction error.
    """
    fields = _plugin_manifest_fields()
    fields["minimum_kernel_version"] = "999.0.0"

    manifest = create_manifest(**fields)

    assert manifest.minimum_kernel_version == "999.0.0"
