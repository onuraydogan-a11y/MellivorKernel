"""Tests for mellivor_kernel.agents.events."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.agents import AgentCompleted, AgentFailed, AgentStarted
from mellivor_kernel.events import Event


def test_agent_started_carries_identifying_fields() -> None:
    event = AgentStarted(agent_id="abc", name="greeter")

    assert isinstance(event, Event)
    assert event.agent_id == "abc"
    assert event.name == "greeter"
    assert event.event_id


def test_agent_completed_carries_identifying_fields() -> None:
    event = AgentCompleted(agent_id="abc", name="greeter")

    assert event.agent_id == "abc"
    assert event.name == "greeter"


def test_agent_failed_carries_error() -> None:
    event = AgentFailed(agent_id="abc", name="greeter", error="boom")

    assert event.error == "boom"


def test_agent_events_are_immutable() -> None:
    event = AgentStarted(agent_id="abc", name="greeter")

    with pytest.raises(dataclasses.FrozenInstanceError):
        event.name = "other"  # type: ignore[misc]
