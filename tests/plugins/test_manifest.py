"""Tests for mellivor_kernel.plugins.manifest."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.plugins import PluginCapability, PluginManifest, PluginValidationError


def test_manifest_holds_all_fields() -> None:
    capability = PluginCapability(name="workflow.step")

    manifest = PluginManifest(
        id="example",
        name="Example Plugin",
        version="1.0.0",
        description="An example plugin.",
        author="Mellivor Security",
        capabilities=frozenset({capability}),
        minimum_kernel_version="0.13.0",
    )

    assert manifest.id == "example"
    assert manifest.name == "Example Plugin"
    assert manifest.version == "1.0.0"
    assert manifest.description == "An example plugin."
    assert manifest.author == "Mellivor Security"
    assert manifest.capabilities == frozenset({capability})
    assert manifest.minimum_kernel_version == "0.13.0"


def test_manifest_capabilities_and_minimum_kernel_version_have_defaults() -> None:
    manifest = PluginManifest(
        id="example", name="Example", version="1.0.0", description="", author="Someone"
    )

    assert manifest.capabilities == frozenset()
    assert manifest.minimum_kernel_version == "0.0.0"


@pytest.mark.parametrize("blank", ["", "   "])
def test_manifest_rejects_blank_id(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginManifest(id=blank, name="Example", version="1.0.0", description="", author="Someone")


@pytest.mark.parametrize("blank", ["", "   "])
def test_manifest_rejects_blank_name(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginManifest(id="example", name=blank, version="1.0.0", description="", author="Someone")


@pytest.mark.parametrize("blank", ["", "   "])
def test_manifest_rejects_blank_author(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginManifest(id="example", name="Example", version="1.0.0", description="", author=blank)


@pytest.mark.parametrize("malformed", ["1.0", "1.0.0.0", "v1.0.0", "1.0.x", "", "latest"])
def test_manifest_rejects_malformed_version(malformed: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginManifest(
            id="example", name="Example", version=malformed, description="", author="Someone"
        )


@pytest.mark.parametrize("malformed", ["1.0", "v1.0.0", "not-a-version"])
def test_manifest_rejects_malformed_minimum_kernel_version(malformed: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginManifest(
            id="example",
            name="Example",
            version="1.0.0",
            description="",
            author="Someone",
            minimum_kernel_version=malformed,
        )


def test_manifest_is_immutable() -> None:
    manifest = PluginManifest(
        id="example", name="Example", version="1.0.0", description="", author="Someone"
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.name = "Renamed"  # type: ignore[misc]
