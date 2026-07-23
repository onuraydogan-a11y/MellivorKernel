"""Workflow lifecycle events, published by WorkflowEngine.

These are ``workflow``'s own event types, not part of the generic
``events`` subsystem -- ``events`` stays free of any knowledge of
"workflow" as a concept, the same reasoning ``execution``'s and
``authorization``'s own event types already follow (see ADR-0008).
"""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.events import Event


@dataclass(frozen=True, slots=True)
class WorkflowStarted(Event):
    """Published once, at the start of :meth:`WorkflowEngine.run`.

    Attributes:
        workflow_id: The run's own id, for correlation with the eventual
            :class:`WorkflowCompleted`/:class:`WorkflowFailed`.
        name: The workflow definition's name.
    """

    workflow_id: str
    name: str


@dataclass(frozen=True, slots=True)
class WorkflowCompleted(Event):
    """Published when a workflow run completes without being stopped early.

    Attributes:
        workflow_id: The run's own id.
        name: The workflow definition's name.
        step_count: How many steps ran.
    """

    workflow_id: str
    name: str
    step_count: int


@dataclass(frozen=True, slots=True)
class WorkflowFailed(Event):
    """Published when a step stops a workflow run early.

    Attributes:
        workflow_id: The run's own id.
        name: The workflow definition's name.
        error: The failure's human-readable description.
        stopped_at: The name of the step that stopped the workflow.
    """

    workflow_id: str
    name: str
    error: str
    stopped_at: str | None = None
