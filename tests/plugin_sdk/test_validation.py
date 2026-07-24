"""Tests for mellivor_kernel.plugin_sdk.validation."""

from __future__ import annotations

from mellivor_kernel.plugin_sdk import (
    create_capability,
    is_valid_capability,
    is_valid_manifest,
    is_valid_metadata,
)


def test_is_valid_capability_true_for_a_valid_name() -> None:
    assert is_valid_capability("workflow.step") is True


def test_is_valid_capability_false_for_a_blank_name() -> None:
    assert is_valid_capability("") is False
    assert is_valid_capability("   ") is False


def test_is_valid_metadata_true_for_valid_fields() -> None:
    assert is_valid_metadata(id="example", name="Example", version="1.0.0") is True


def test_is_valid_metadata_false_for_a_blank_id() -> None:
    assert is_valid_metadata(id="", name="Example", version="1.0.0") is False


def test_is_valid_metadata_false_for_a_blank_version() -> None:
    """`PluginMetadata` validates blankness only, not `MAJOR.MINOR.PATCH`
    format -- unlike `PluginManifest`. This helper must not invent
    stricter validation than the runtime contract it delegates to.
    """
    assert is_valid_metadata(id="example", name="Example", version="") is False


def test_is_valid_manifest_true_for_valid_fields() -> None:
    assert (
        is_valid_manifest(id="example", name="Example", version="1.0.0", author="Someone") is True
    )


def test_is_valid_manifest_false_for_a_blank_author() -> None:
    assert is_valid_manifest(id="example", name="Example", version="1.0.0", author="") is False


def test_is_valid_manifest_false_for_a_malformed_minimum_kernel_version() -> None:
    assert (
        is_valid_manifest(
            id="example",
            name="Example",
            version="1.0.0",
            author="Someone",
            minimum_kernel_version="not-a-version",
        )
        is False
    )


def test_is_valid_manifest_true_with_capabilities() -> None:
    capability = create_capability("workflow.step")

    assert (
        is_valid_manifest(
            id="example",
            name="Example",
            version="1.0.0",
            author="Someone",
            capabilities=[capability],
        )
        is True
    )
