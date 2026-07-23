"""Public API of the kernel's workflow subsystem.

The workflow engine orchestrates multiple execution steps -- it never
executes a tool or provider itself. Every step is delegated to
:class:`~mellivor_kernel.execution.engine.ExecutionEngine`, the kernel's
single execution entry point; ``workflow`` composes calls to it and never
duplicates, bypasses, or reimplements anything ``execution`` already does.

``workflow`` depends on ``execution``, ``memory``, and ``events``;
``execution`` (and every subsystem below it) has no dependency on
``workflow`` and never will -- see ADR-0010. Sequential execution only:
no parallel steps, no scheduling, no cron, no persistence beyond whatever
``memory`` itself provides.
"""

from __future__ import annotations

from mellivor_kernel.workflow.context import WorkflowContext
from mellivor_kernel.workflow.definition import WorkflowDefinition
from mellivor_kernel.workflow.engine import WorkflowEngine
from mellivor_kernel.workflow.events import WorkflowCompleted, WorkflowFailed, WorkflowStarted
from mellivor_kernel.workflow.exceptions import WorkflowError
from mellivor_kernel.workflow.result import WorkflowResult
from mellivor_kernel.workflow.step import WorkflowStep
from mellivor_kernel.workflow.workflow import Workflow

__all__ = [
    "Workflow",
    "WorkflowCompleted",
    "WorkflowContext",
    "WorkflowDefinition",
    "WorkflowEngine",
    "WorkflowError",
    "WorkflowFailed",
    "WorkflowResult",
    "WorkflowStarted",
    "WorkflowStep",
]
