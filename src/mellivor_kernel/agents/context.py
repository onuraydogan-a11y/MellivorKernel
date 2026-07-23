"""AgentContext: the shared context an agent run executes with."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.workflow import WorkflowContext


@dataclass(frozen=True, slots=True)
class AgentContext:
    """The context an agent run executes with.

    Deliberately thin: this sprint's agent runtime invokes exactly one
    workflow per run (no planning, no multi-agent composition), so the
    only thing that needs to be "shared" is the same
    :class:`~mellivor_kernel.workflow.WorkflowContext` -- and, through it,
    the same :class:`~mellivor_kernel.execution.ExecutionContext` -- passed
    down to :class:`~mellivor_kernel.workflow.WorkflowEngine`.

    Attributes:
        workflow_context: The context passed to
            ``WorkflowEngine.run()`` when this agent's workflow is
            invoked.
    """

    workflow_context: WorkflowContext
