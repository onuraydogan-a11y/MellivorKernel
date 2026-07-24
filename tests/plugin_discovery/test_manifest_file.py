"""Tests for mellivor_kernel.plugin_discovery.manifest_file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mellivor_kernel.plugin_discovery.exceptions import ManifestNotFoundError, ManifestParseError
from mellivor_kernel.plugin_discovery.manifest_file import read_manifest_file
from mellivor_kernel.plugins import PluginManifest, PluginValidationError


def _write_manifest(path: Path, data: dict[str, object]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "example",
        "name": "Example Plugin",
        "version": "1.0.0",
        "description": "An example plugin.",
        "author": "Someone",
        "minimum_kernel_version": "0.13.0",
        "capabilities": [{"name": "kernel.introspection", "description": "Read-only info."}],
        "entry_point": "package.module:PluginClass",
    }
    data.update(overrides)
    return data


def test_reads_a_valid_manifest(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path / "plugin_manifest.json", _valid_data())

    manifest, entry_point = read_manifest_file(manifest_path)

    assert isinstance(manifest, PluginManifest)
    assert manifest.id == "example"
    assert manifest.author == "Someone"
    assert manifest.minimum_kernel_version == "0.13.0"
    assert {c.name for c in manifest.capabilities} == {"kernel.introspection"}
    assert entry_point == "package.module:PluginClass"


def test_missing_optional_fields_use_defaults(tmp_path: Path) -> None:
    data = _valid_data()
    del data["description"]
    del data["minimum_kernel_version"]
    del data["capabilities"]
    manifest_path = _write_manifest(tmp_path / "plugin_manifest.json", data)

    manifest, _ = read_manifest_file(manifest_path)

    assert manifest.description == ""
    assert manifest.minimum_kernel_version == "0.0.0"
    assert manifest.capabilities == frozenset()


def test_missing_file_raises_manifest_not_found(tmp_path: Path) -> None:
    with pytest.raises(ManifestNotFoundError):
        read_manifest_file(tmp_path / "does_not_exist.json")


def test_invalid_json_raises_manifest_parse_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "plugin_manifest.json"
    manifest_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_non_object_json_raises_manifest_parse_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "plugin_manifest.json"
    manifest_path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


@pytest.mark.parametrize("missing_field", ["id", "name", "version", "author"])
def test_missing_required_field_raises_manifest_parse_error(
    tmp_path: Path, missing_field: str
) -> None:
    data = _valid_data()
    del data[missing_field]
    manifest_path = _write_manifest(tmp_path / "plugin_manifest.json", data)

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_missing_entry_point_raises_manifest_parse_error(tmp_path: Path) -> None:
    data = _valid_data()
    del data["entry_point"]
    manifest_path = _write_manifest(tmp_path / "plugin_manifest.json", data)

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_blank_entry_point_raises_manifest_parse_error(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "plugin_manifest.json", _valid_data(entry_point="  ")
    )

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_non_list_capabilities_raises_manifest_parse_error(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "plugin_manifest.json", _valid_data(capabilities="not-a-list")
    )

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_capability_missing_name_raises_manifest_parse_error(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "plugin_manifest.json",
        _valid_data(capabilities=[{"description": "no name field"}]),
    )

    with pytest.raises(ManifestParseError):
        read_manifest_file(manifest_path)


def test_invalid_field_value_propagates_plugin_validation_error(tmp_path: Path) -> None:
    """A structurally well-formed manifest with an invalid field value
    (blank id) must raise `PluginValidationError` from `PluginManifest`
    itself -- not a discovery-specific error, and not duplicated logic.
    """
    manifest_path = _write_manifest(tmp_path / "plugin_manifest.json", _valid_data(id=""))

    with pytest.raises(PluginValidationError):
        read_manifest_file(manifest_path)


def test_invalid_version_format_propagates_plugin_validation_error(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "plugin_manifest.json", _valid_data(version="not-a-version")
    )

    with pytest.raises(PluginValidationError):
        read_manifest_file(manifest_path)
