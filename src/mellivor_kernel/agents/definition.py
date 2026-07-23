"""AgentDefinition: the declarative, reusable structure of an agent."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.agents.exceptions import AgentError
from mellivor_kernel.workflow import WorkflowDefinition


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """An immutable, reusable definition of an agent.

    An agent is deliberately thin at this sprint's scope: it names a
    single :class:`~mellivor_kernel.workflow.WorkflowDefinition` to
    invoke. No planning, no reasoning, no reflection, and no multi-agent
    composition -- an agent does not choose or sequence workflows
    dynamically; it always runs the one it was configured with.

    Attributes:
        name: A human-readable name for this agent.
        workflow: The workflow definition this agent invokes when
            executed.
        metadata: Additional, agent-specific information (for example an
            owning team or a version tag).
    """

    name: str
    workflow: WorkflowDefinition
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            AgentError: If ``name`` is blank.
        """
        if not self.name.strip():
            raise AgentError("AgentDefinition.name must not be blank.")
