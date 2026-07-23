"""Tests for mellivor_kernel.agents.definition."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.agents import AgentDefinition, AgentError
from mellivor_kernel.workflow import WorkflowDefinition


def _workflow() -> WorkflowDefinition:
    return WorkflowDefinition(name="greet")


def test_definition_defaults() -> None:
    workflow = _workflow()
    definition = AgentDefinition(name="greeter", workflow=workflow)

    assert definition.name == "greeter"
    assert definition.workflow is workflow
    assert dict(definition.metadata) == {}


def test_definition_accepts_metadata() -> None:
    definition = AgentDefinition(name="greeter", workflow=_workflow(), metadata={"owner": "team-x"})

    assert definition.metadata == {"owner": "team-x"}


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_name_rejected(blank: str) -> None:
    with pytest.raises(AgentError):
        AgentDefinition(name=blank, workflow=_workflow())


def test_definition_is_immutable() -> None:
    definition = AgentDefinition(name="greeter", workflow=_workflow())

    with pytest.raises(dataclasses.FrozenInstanceError):
        definition.name = "other"  # type: ignore[misc]
