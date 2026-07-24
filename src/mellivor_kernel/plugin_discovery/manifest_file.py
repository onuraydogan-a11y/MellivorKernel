"""Reads and parses a plugin manifest file into a `PluginManifest` and its
discovery-only `entry_point` string.
"""

from __future__ import annotations

import json
from pathlib import Path

from mellivor_kernel.plugin_discovery.exceptions import ManifestNotFoundError, ManifestParseError
from mellivor_kernel.plugins import PluginCapability, PluginManifest

_REQUIRED_FIELDS = ("id", "name", "version", "author")


def read_manifest_file(path: Path) -> tuple[PluginManifest, str]:
    """Read and parse the manifest file at `path`.

    Args:
        path: The manifest file's path.

    Returns:
        A `(manifest, entry_point)` pair: the constructed `PluginManifest`
        and the raw, unresolved `entry_point` string
        (`"module.path:AttributeName"`).

    Raises:
        ManifestNotFoundError: If `path` does not exist.
        ManifestParseError: If the file is not valid JSON, is not a JSON
            object, or is missing a required discovery-level field.
        PluginValidationError: If a present field's value is invalid --
            raised by `PluginManifest.__post_init__`/
            `PluginCapability.__post_init__` themselves, never duplicated
            here.
    """
    if not path.is_file():
        raise ManifestNotFoundError(f"No manifest file found at {path}.")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestParseError(f"Could not read {path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ManifestParseError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestParseError(f"{path} must contain a JSON object at the top level.")

    missing = [field for field in _REQUIRED_FIELDS if field not in data]
    if missing:
        raise ManifestParseError(f"{path} is missing required field(s): {', '.join(missing)}.")

    entry_point = data.get("entry_point")
    if not isinstance(entry_point, str) or not entry_point.strip():
        raise ManifestParseError(f"{path} is missing a non-empty 'entry_point' string.")

    capabilities_data = data.get("capabilities", [])
    if not isinstance(capabilities_data, list):
        raise ManifestParseError(f"{path}: 'capabilities' must be a list.")
    capabilities = tuple(_parse_capability(path, entry) for entry in capabilities_data)

    manifest = PluginManifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        description=data.get("description", ""),
        author=data["author"],
        capabilities=frozenset(capabilities),
        minimum_kernel_version=data.get("minimum_kernel_version", "0.0.0"),
    )
    return manifest, entry_point


def _parse_capability(path: Path, entry: object) -> PluginCapability:
    """Parse one `capabilities` list entry into a `PluginCapability`."""
    if not isinstance(entry, dict) or "name" not in entry:
        raise ManifestParseError(
            f"{path}: each entry in 'capabilities' must be an object with a 'name' field."
        )
    return PluginCapability(name=entry["name"], description=entry.get("description", ""))
