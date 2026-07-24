"""Tests for mellivor_kernel.plugins.capability."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugins import PluginCapability, PluginValidationError


def test_capability_holds_name_and_description() -> None:
    capability = PluginCapability(name="workflow.step", description="Runs a workflow step.")

    assert capability.name == "workflow.step"
    assert capability.description == "Runs a workflow step."


def test_capability_description_defaults_to_empty() -> None:
    capability = PluginCapability(name="workflow.step")

    assert capability.description == ""


@pytest.mark.parametrize("blank", ["", "   "])
def test_capability_rejects_blank_name(blank: str) -> None:
    with pytest.raises(PluginValidationError):
        PluginCapability(name=blank)


def test_capability_is_hashable_for_use_in_a_frozenset() -> None:
    first = PluginCapability(name="workflow.step")
    second = PluginCapability(name="workflow.step")

    assert first == second
    assert frozenset({first, second}) == {first}
