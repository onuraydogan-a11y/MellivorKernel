"""Workflow: a single, identified run of a WorkflowDefinition."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mellivor_kernel.workflow.definition import WorkflowDefinition


@dataclass(frozen=True, slots=True)
class Workflow:
    """A single run of a :class:`WorkflowDefinition`, identified for correlation.

    Attributes:
        definition: The reusable, declarative structure being run.
        workflow_id: A unique identifier for this specific run, for log,
            event, and memory correlation. Auto-generated if not supplied.
    """

    definition: WorkflowDefinition
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
