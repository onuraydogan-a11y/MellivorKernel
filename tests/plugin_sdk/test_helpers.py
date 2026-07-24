"""Tests for mellivor_kernel.plugin_sdk.helpers."""

from __future__ import annotations

import ast
import inspect

import pytest

from mellivor_kernel.plugin_sdk import create_capability, create_manifest, create_metadata, helpers
from mellivor_kernel.plugins import (
    PluginCapability,
    PluginManifest,
    PluginMetadata,
    PluginValidationError,
)


def test_create_capability_returns_a_plugin_capability() -> None:
    capability = create_capability("workflow.step", "Runs a workflow step.")

    assert isinstance(capability, PluginCapability)
    assert capability.name == "workflow.step"
    assert capability.description == "Runs a workflow step."


def test_create_capability_description_defaults_to_empty() -> None:
    capability = create_capability("workflow.step")

    assert capability.description == ""


def test_create_capability_rejects_blank_name() -> None:
    with pytest.raises(PluginValidationError):
        create_capability("")


def test_create_manifest_returns_a_plugin_manifest() -> None:
    capability = create_capability("workflow.step")

    manifest = create_manifest(
        id="example",
        name="Example",
        version="1.0.0",
        author="Someone",
        description="An example plugin.",
        capabilities=[capability],
        minimum_kernel_version="0.13.0",
    )

    assert isinstance(manifest, PluginManifest)
    assert manifest.id == "example"
    assert manifest.author == "Someone"
    assert manifest.capabilities == frozenset({capability})
    assert manifest.minimum_kernel_version == "0.13.0"


def test_create_manifest_uses_defaults_for_optional_fields() -> None:
    manifest = create_manifest(id="example", name="Example", version="1.0.0", author="Someone")

    assert manifest.description == ""
    assert manifest.capabilities == frozenset()
    assert manifest.minimum_kernel_version == "0.0.0"


def test_create_manifest_rejects_invalid_fields() -> None:
    with pytest.raises(PluginValidationError):
        create_manifest(id="", name="Example", version="1.0.0", author="Someone")


def test_create_metadata_returns_a_plugin_metadata() -> None:
    capability = create_capability("workflow.step")

    metadata = create_metadata(
        id="example",
        name="Example",
        version="1.0.0",
        description="An example plugin.",
        capabilities=[capability],
    )

    assert isinstance(metadata, PluginMetadata)
    assert metadata.id == "example"
    assert metadata.capabilities == frozenset({capability})


def test_create_metadata_uses_defaults_for_optional_fields() -> None:
    metadata = create_metadata(id="example", name="Example", version="1.0.0")

    assert metadata.description == ""
    assert metadata.capabilities == frozenset()


def test_create_metadata_rejects_invalid_fields() -> None:
    with pytest.raises(PluginValidationError):
        create_metadata(id="example", name="", version="1.0.0")


def test_helpers_perform_no_registration() -> None:
    """`create_manifest`/`create_metadata`/`create_capability` construct
    value objects only -- none of them accepts, imports, or calls
    `PluginRegistry`.
    """
    for func in (create_capability, create_manifest, create_metadata):
        signature = inspect.signature(func)
        assert "registry" not in signature.parameters

    tree = ast.parse(inspect.getsource(helpers))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "PluginRegistry" not in imported_names
