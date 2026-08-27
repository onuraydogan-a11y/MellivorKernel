"""WorkflowStep: a single unit of work within a workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.workflow.context import WorkflowContext
from mellivor_kernel.workflow.exceptions import WorkflowError


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """A single step in a :class:`~mellivor_kernel.workflow.definition.WorkflowDefinition`.

    A step never executes anything itself -- it only names the
    :class:`~mellivor_kernel.execution.request.ExecutionRequest` that
    :class:`~mellivor_kernel.workflow.engine.WorkflowEngine` delegates to
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`, either
    statically (:attr:`request`) or dynamically
    (:attr:`request_factory`) -- see ADR-0024.

    Attributes:
        name: A unique, human-readable identifier for this step within
            its workflow -- used as the key in
            :attr:`~mellivor_kernel.workflow.result.WorkflowResult.step_results`.
        request: The static request this step delegates to
            ``ExecutionEngine``. Exactly one of ``request``/
            ``request_factory`` must be set.
        granted_permissions: The permission identifiers (as raw strings)
            claimed for this step's execution -- forwarded unchanged to
            ``ExecutionEngine.execute()``.
        continue_on_failure: If ``True``, a failed outcome for this step
            does not stop the workflow -- the next step still runs.
            Defaults to ``False``: by default, any failed step stops the
            workflow.
        request_factory: Builds this step's ``ExecutionRequest`` at run
            time from the accumulated :class:`~mellivor_kernel.workflow.context.WorkflowContext`
            -- for example, reading an earlier step's result from
            ``context.step_results``. A plain callable, never evaluated
            or interpreted by the kernel; if it raises, or returns
            anything other than an ``ExecutionRequest``, this step fails
            with ``metadata["stage"] == "dynamic_request"``, the same way
            any other step failure is represented. Exactly one of
            ``request``/``request_factory`` must be set.
        parallel_group: If set, this step runs concurrently with every
            other step sharing the same value, provided they are
            contiguous in their workflow's ``steps`` (enforced by
            :class:`~mellivor_kernel.workflow.definition.WorkflowDefinition`).
            ``None`` (the default) means this step runs on its own, in
            the calling thread -- the pre-Sprint-30 behavior, unchanged.
        not_before: If set, this step does not run before this
            timezone-aware moment (per the engine's configured
            :class:`~mellivor_kernel.workflow.clock.Clock`). A step
            invoked too early fails with ``metadata["stage"] ==
            "scheduling"`` rather than running -- it is never blocked or
            delayed. ``None`` (the default) means no scheduling
            constraint.
    """

    name: str
    request: ExecutionRequest | None = None
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    continue_on_failure: bool = False
    request_factory: Callable[[WorkflowContext], ExecutionRequest] | None = None
    parallel_group: str | None = None
    not_before: datetime | None = None

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            WorkflowError: If ``name`` is blank; if both or neither of
                ``request``/``request_factory`` is set; if
                ``parallel_group`` is set but blank; or if ``not_before``
                is set but not timezone-aware.
        """
        if not self.name.strip():
            raise WorkflowError("WorkflowStep.name must not be blank.")
        if (self.request is None) == (self.request_factory is None):
            raise WorkflowError(
                "WorkflowStep must set exactly one of `request` (static) or "
                "`request_factory` (dynamic)."
            )
        if self.parallel_group is not None and not self.parallel_group.strip():
            raise WorkflowError("WorkflowStep.parallel_group must not be blank if set.")
        if self.not_before is not None and self.not_before.tzinfo is None:
            raise WorkflowError("WorkflowStep.not_before must be timezone-aware if set.")
