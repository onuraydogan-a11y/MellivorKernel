"""AgentResult: the outcome of a single agent run."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.agents.exceptions import AgentError
from mellivor_kernel.workflow import WorkflowResult


@dataclass(frozen=True, slots=True)
class AgentResult:
    """The immutable outcome of a single ``AgentEngine.execute()`` call.

    ``success`` mirrors ``workflow_result.success`` directly -- an
    agent's only job, at this sprint's scope, is invoking its one
    workflow, so the agent succeeds exactly when that workflow does.

    Attributes:
        success: Whether the invoked workflow completed without being
            stopped early.
        workflow_result: The outcome of invoking this agent's workflow.
            Always present -- ``WorkflowEngine.run()`` never raises for a
            normal failure, so an ``AgentResult`` always has one to
            report, whether the run succeeded or failed.
        error: A human-readable failure description. Required (non-empty)
            when ``success`` is ``False``; must be unset on success.
    """

    success: bool
    workflow_result: WorkflowResult
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            AgentError: If ``success`` is ``False`` and ``error`` is not
                a non-empty string, or if ``success`` is ``True`` and
                ``error`` is set.
        """
        if not self.success and not (self.error and self.error.strip()):
            raise AgentError("A failed AgentResult must include a non-empty `error` message.")
        if self.success and self.error is not None:
            raise AgentError("A successful AgentResult must not set `error`.")
