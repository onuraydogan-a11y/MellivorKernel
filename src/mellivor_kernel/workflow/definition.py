"""WorkflowDefinition: the declarative, reusable structure of a workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.workflow.exceptions import WorkflowError
from mellivor_kernel.workflow.step import WorkflowStep


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """An immutable, reusable definition of a sequence of steps.

    A definition is a "recipe" -- it carries no run identity. Each run of
    it is a :class:`~mellivor_kernel.workflow.workflow.Workflow`.

    Attributes:
        name: A human-readable name for this workflow.
        steps: The steps to run, in order. May be empty -- an empty
            workflow completes trivially, successfully, with no steps
            run.
        metadata: Additional, workflow-specific information (for example
            an owning team or a version tag).
    """

    name: str
    steps: tuple[WorkflowStep, ...] = field(default_factory=tuple)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            WorkflowError: If ``name`` is blank, or if ``steps`` contains
                two steps with the same ``name`` -- a duplicate would
                silently overwrite the earlier step's entry in
                :attr:`~mellivor_kernel.workflow.result.WorkflowResult.step_results`.
        """
        if not self.name.strip():
            raise WorkflowError("WorkflowDefinition.name must not be blank.")
        names = [step.name for step in self.steps]
        if len(names) != len(set(names)):
            raise WorkflowError("WorkflowDefinition.steps must have unique names.")
