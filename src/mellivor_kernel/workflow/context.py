"""WorkflowContext: the shared context threaded across a workflow's steps."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.result import ExecutionResult


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """The context shared across every step of one workflow run.

    Attributes:
        execution_context: The :class:`~mellivor_kernel.execution.context.ExecutionContext`
            passed to ``ExecutionEngine`` for every step -- identical for
            the whole run.
        step_results: The outcome of every step completed so far, keyed
            by step name. Empty at the start of a run;
            :class:`~mellivor_kernel.workflow.engine.WorkflowEngine`
            threads a new ``WorkflowContext`` with this updated after each
            step, so a later step's caller can inspect earlier steps'
            outcomes -- this is what makes the context "shared."
    """

    execution_context: ExecutionContext
    step_results: Mapping[str, ExecutionResult] = field(default_factory=dict)
