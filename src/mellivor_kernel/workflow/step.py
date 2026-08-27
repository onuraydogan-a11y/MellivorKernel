"""WorkflowStep: a single unit of work within a workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.workflow.exceptions import WorkflowError


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """A single step in a :class:`~mellivor_kernel.workflow.definition.WorkflowDefinition`.

    A step never executes anything itself -- it only names the
    :class:`~mellivor_kernel.execution.request.ExecutionRequest` that
    :class:`~mellivor_kernel.workflow.engine.WorkflowEngine` delegates to
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`.

    Attributes:
        name: A unique, human-readable identifier for this step within
            its workflow -- used as the key in
            :attr:`~mellivor_kernel.workflow.result.WorkflowResult.step_results`.
        request: The request this step delegates to ``ExecutionEngine``.
        granted_permissions: The permission identifiers (as raw strings)
            claimed for this step's execution -- forwarded unchanged to
            ``ExecutionEngine.execute()``.
        continue_on_failure: If ``True``, a failed outcome for this step
            does not stop the workflow -- the next step still runs.
            Defaults to ``False``: by default, any failed step stops the
            workflow.
    """

    name: str
    request: ExecutionRequest
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    continue_on_failure: bool = False

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            WorkflowError: If ``name`` is blank.
        """
        if not self.name.strip():
            raise WorkflowError("WorkflowStep.name must not be blank.")
