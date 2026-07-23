"""WorkflowResult: the outcome of a single workflow run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.execution.result import ExecutionResult
from mellivor_kernel.workflow.exceptions import WorkflowError


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """The immutable outcome of a single ``WorkflowEngine.run()`` call.

    ``success`` tracks whether the workflow ran to completion without
    being stopped early -- not whether every individual step succeeded. A
    step that fails with :attr:`~mellivor_kernel.workflow.step.WorkflowStep.continue_on_failure`
    set does not stop the workflow, so it can still complete
    successfully; callers wanting to know whether *any* step failed
    should inspect :attr:`step_results` directly.

    Attributes:
        success: ``True`` unless a step failed and stopped the workflow
            (``stopped_at`` is ``None`` iff ``success`` is ``True``). An
            empty workflow is trivially successful.
        step_results: The outcome of every step that ran, keyed by step
            name, in execution order.
        error: A human-readable failure description naming the step that
            stopped the workflow. Required (non-empty) when ``success``
            is ``False``; must be unset on success.
        stopped_at: The name of the step whose failure stopped the
            workflow. Must be unset on success.
    """

    success: bool
    step_results: Mapping[str, ExecutionResult] = field(default_factory=dict)
    error: str | None = None
    stopped_at: str | None = None

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            WorkflowError: If ``success`` is ``False`` and ``error`` is
                not a non-empty string, or if ``success`` is ``True`` and
                ``error`` or ``stopped_at`` is set.
        """
        if not self.success and not (self.error and self.error.strip()):
            raise WorkflowError("A failed WorkflowResult must include a non-empty `error` message.")
        if self.success and self.error is not None:
            raise WorkflowError("A successful WorkflowResult must not set `error`.")
        if self.success and self.stopped_at is not None:
            raise WorkflowError("A successful WorkflowResult must not set `stopped_at`.")
