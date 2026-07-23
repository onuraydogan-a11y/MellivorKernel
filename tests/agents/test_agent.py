"""Tests for mellivor_kernel.agents.agent."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.agents import Agent, AgentDefinition
from mellivor_kernel.workflow import WorkflowDefinition


def _definition() -> AgentDefinition:
    return AgentDefinition(name="greeter", workflow=WorkflowDefinition(name="greet"))


def test_agent_auto_generates_id() -> None:
    definition = _definition()
    agent = Agent(definition=definition)

    assert isinstance(agent.agent_id, str) and agent.agent_id
    assert agent.definition is definition


def test_agent_ids_are_unique() -> None:
    definition = _definition()

    first = Agent(definition=definition)
    second = Agent(definition=definition)

    assert first.agent_id != second.agent_id


def test_agent_accepts_explicit_id() -> None:
    agent = Agent(definition=_definition(), agent_id="fixed-id")

    assert agent.agent_id == "fixed-id"


def test_agent_is_immutable() -> None:
    agent = Agent(definition=_definition())

    with pytest.raises(dataclasses.FrozenInstanceError):
        agent.agent_id = "other"  # type: ignore[misc]
