"""Workflow subsystem exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class WorkflowError(KernelError):
    """Base class for all errors raised by the workflow subsystem.

    Raised only for invalid data (a malformed
    :class:`~mellivor_kernel.workflow.step.WorkflowStep`,
    :class:`~mellivor_kernel.workflow.definition.WorkflowDefinition`, or
    :class:`~mellivor_kernel.workflow.result.WorkflowResult`) -- a step
    failing during a run is a normal, non-raising outcome, represented in
    :class:`~mellivor_kernel.workflow.result.WorkflowResult`.
    """
