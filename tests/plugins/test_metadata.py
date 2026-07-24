"""Tests for mellivor_kernel.plugins.metadata."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.plugins import PluginCapability, PluginMetadata, PluginValidationError


def test_metadata_holds_all_fields() -> None:
    capability = PluginCapability(name="workflow.step")

    metadata = PluginMetadata(
        id="example",
        name="Example Plugin",
        version="1.0.0",
        description="An example plugin.",
        capabilities=frozenset({capability}),
    )

    assert metadata.id == "example"
    assert metadata.name == "Example Plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "An example plugin."
    assert metadata.capabilities == frozenset({capability})


def test_metadata_capabilities_default_to_empty() -> None:
    metadata = PluginMetadata(id="example", name="Example", version="1.0.0", description="")

    assert metadata.capabilities == frozenset()


@pytest.mark.parametrize("blank", ["", "   "])
def test_metadata_rejects_blank_id(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginMetadata(id=blank, name="Example", version="1.0.0", description="")


@pytest.mark.parametrize("blank", ["", "   "])
def test_metadata_rejects_blank_name(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginMetadata(id="example", name=blank, version="1.0.0", description="")


@pytest.mark.parametrize("blank", ["", "   "])
def test_metadata_rejects_blank_version(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginMetadata(id="example", name="Example", version=blank, description="")


def test_metadata_is_immutable() -> None:
    metadata = PluginMetadata(id="example", name="Example", version="1.0.0", description="")

    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.name = "Renamed"  # type: ignore[misc]
