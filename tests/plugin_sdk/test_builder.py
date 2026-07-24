"""Tests for mellivor_kernel.plugin_sdk.builder."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugin_sdk import PluginBuilder
from mellivor_kernel.plugins import PluginManifest, PluginMetadata, PluginValidationError


def test_build_manifest_produces_all_fields() -> None:
    manifest = (
        PluginBuilder()
        .with_id("example")
        .with_name("Example Plugin")
        .with_version("1.0.0")
        .with_author("Mellivor Security")
        .with_description("An example plugin.")
        .with_capability("workflow.step", "Runs a workflow step.")
        .with_minimum_kernel_version("0.13.0")
        .build_manifest()
    )

    assert isinstance(manifest, PluginManifest)
    assert manifest.id == "example"
    assert manifest.name == "Example Plugin"
    assert manifest.version == "1.0.0"
    assert manifest.author == "Mellivor Security"
    assert manifest.description == "An example plugin."
    assert manifest.minimum_kernel_version == "0.13.0"
    assert {capability.name for capability in manifest.capabilities} == {"workflow.step"}


def test_build_metadata_produces_all_fields_but_no_author_or_minimum_kernel_version() -> None:
    metadata = (
        PluginBuilder()
        .with_id("example")
        .with_name("Example Plugin")
        .with_version("1.0.0")
        .with_author("Ignored for metadata")
        .with_description("An example plugin.")
        .with_capability("workflow.step")
        .with_minimum_kernel_version("9.9.9")
        .build_metadata()
    )

    assert isinstance(metadata, PluginMetadata)
    assert metadata.id == "example"
    assert metadata.name == "Example Plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "An example plugin."
    assert {capability.name for capability in metadata.capabilities} == {"workflow.step"}
    assert not hasattr(metadata, "author")
    assert not hasattr(metadata, "minimum_kernel_version")


def test_with_capabilities_replaces_the_accumulated_set() -> None:
    builder = PluginBuilder().with_capability("a").with_capability("b")

    builder.with_capabilities()

    metadata = builder.with_id("x").with_name("X").with_version("1.0.0").build_metadata()
    assert metadata.capabilities == frozenset()


def test_with_capability_accumulates_rather_than_overwrites() -> None:
    manifest = (
        PluginBuilder()
        .with_id("x")
        .with_name("X")
        .with_version("1.0.0")
        .with_author("Someone")
        .with_capability("a")
        .with_capability("b")
        .build_manifest()
    )

    assert {capability.name for capability in manifest.capabilities} == {"a", "b"}


def test_build_manifest_without_setting_id_raises_the_runtime_error() -> None:
    with pytest.raises(PluginValidationError):
        PluginBuilder().with_name("X").with_version("1.0.0").with_author("Someone").build_manifest()


def test_build_manifest_with_malformed_version_raises_the_runtime_error() -> None:
    with pytest.raises(PluginValidationError):
        (
            PluginBuilder()
            .with_id("x")
            .with_name("X")
            .with_version("not-a-version")
            .with_author("Someone")
            .build_manifest()
        )


def test_builder_methods_return_the_same_builder_for_chaining() -> None:
    builder = PluginBuilder()

    assert builder.with_id("x") is builder
    assert builder.with_name("X") is builder
    assert builder.with_version("1.0.0") is builder
    assert builder.with_author("Someone") is builder
    assert builder.with_description("desc") is builder
    assert builder.with_capability("cap") is builder
    assert builder.with_capabilities() is builder
    assert builder.with_minimum_kernel_version("0.0.0") is builder
