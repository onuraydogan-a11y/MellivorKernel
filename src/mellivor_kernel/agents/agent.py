"""Agent: a single, identified run of an AgentDefinition."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mellivor_kernel.agents.definition import AgentDefinition


@dataclass(frozen=True, slots=True)
class Agent:
    """A single run of an :class:`AgentDefinition`, identified for correlation.

    Attributes:
        definition: The reusable, declarative structure being run.
        agent_id: A unique identifier for this specific run, for log,
            event, and memory correlation. Auto-generated if not
            supplied.
    """

    definition: AgentDefinition
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
