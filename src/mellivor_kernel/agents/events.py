"""Agent lifecycle events, published by AgentEngine.

These are ``agents``' own event types, not part of the generic ``events``
subsystem -- ``events`` stays free of any knowledge of "agent" as a
concept, the same reasoning ``execution``'s, ``authorization``'s, and
``workflow``'s own event types already follow (see ADR-0008).
"""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.events import Event


@dataclass(frozen=True, slots=True)
class AgentStarted(Event):
    """Published once, at the start of :meth:`AgentEngine.execute`.

    Attributes:
        agent_id: The run's own id, for correlation with the eventual
            :class:`AgentCompleted`/:class:`AgentFailed`.
        name: The agent definition's name.
    """

    agent_id: str
    name: str


@dataclass(frozen=True, slots=True)
class AgentCompleted(Event):
    """Published when an agent run's workflow completes without being stopped early.

    Attributes:
        agent_id: The run's own id.
        name: The agent definition's name.
    """

    agent_id: str
    name: str


@dataclass(frozen=True, slots=True)
class AgentFailed(Event):
    """Published when an agent run's workflow stops early.

    Attributes:
        agent_id: The run's own id.
        name: The agent definition's name.
        error: The failure's human-readable description.
    """

    agent_id: str
    name: str
    error: str
