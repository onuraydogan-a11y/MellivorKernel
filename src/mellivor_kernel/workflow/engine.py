"""WorkflowEngine: orchestrates sequential execution of a workflow's steps."""

from __future__ import annotations

import dataclasses

from mellivor_kernel.events import Event, EventBus
from mellivor_kernel.execution.engine import ExecutionEngine
from mellivor_kernel.execution.result import ExecutionResult
from mellivor_kernel.memory import MemoryEntry, MemoryStore
from mellivor_kernel.workflow.context import WorkflowContext
from mellivor_kernel.workflow.events import WorkflowCompleted, WorkflowFailed, WorkflowStarted
from mellivor_kernel.workflow.result import WorkflowResult
from mellivor_kernel.workflow.workflow import Workflow


class WorkflowEngine:
    """Orchestrates sequential execution of a :class:`Workflow`'s steps.

    Never executes a tool or provider directly, and never performs a
    provider call itself -- every step is delegated to the injected
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`, the
    kernel's single execution entry point. ``WorkflowEngine`` composes
    calls to it; it does not duplicate, bypass, or reimplement any part
    of what ``ExecutionEngine`` already does (authorization, dispatch,
    event publication, memory recording at the execution level).

    Steps run strictly in sequence -- no parallel execution, no
    scheduling, no cron, no persistence beyond whatever ``memory`` itself
    provides. A step's failure stops the workflow unless that step sets
    :attr:`~mellivor_kernel.workflow.step.WorkflowStep.continue_on_failure`.
    """

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        *,
        memory: MemoryStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the engine.

        All infrastructure is received via dependency injection --
        ``WorkflowEngine`` never constructs an ``ExecutionEngine``, a
        memory backend, or an event bus itself.

        Args:
            execution_engine: The engine every step is delegated to.
            memory: The store this workflow run's own outcome is recorded
                to (in addition to whatever ``execution_engine`` itself
                may record per step, if it has its own memory
                configured). If ``None`` (the default), nothing is
                recorded at the workflow level.
            event_bus: The bus lifecycle events are published to. If
                ``None`` (the default), no events are published.
        """
        self._execution_engine = execution_engine
        self._memory = memory
        self._event_bus = event_bus

    def run(self, workflow: Workflow, context: WorkflowContext) -> WorkflowResult:
        """Run every step of ``workflow.definition``, in order.

        Args:
            workflow: The workflow run to execute.
            context: The shared context to run with.

        Returns:
            A :class:`WorkflowResult`. ``success`` is ``True`` unless a
            step fails without ``continue_on_failure``, in which case the
            workflow stops before running any further step.
        """
        definition = workflow.definition
        logger = context.execution_context.logger
        logger.info(
            "Starting workflow %r (%r), %d step(s).",
            workflow.workflow_id,
            definition.name,
            len(definition.steps),
        )
        self._publish(WorkflowStarted(workflow_id=workflow.workflow_id, name=definition.name))

        step_results: dict[str, ExecutionResult] = {}
        running_context = context
        for step in definition.steps:
            result = self._execution_engine.execute(
                step.request,
                running_context.execution_context,
                granted_permissions=step.granted_permissions,
            )
            step_results[step.name] = result
            running_context = dataclasses.replace(running_context, step_results=dict(step_results))

            if not result.success and not step.continue_on_failure:
                workflow_result = WorkflowResult(
                    success=False,
                    step_results=dict(step_results),
                    error=f"Step {step.name!r} failed: {result.error}",
                    stopped_at=step.name,
                )
                logger.warning(
                    "Workflow %r stopped at step %r: %s",
                    workflow.workflow_id,
                    step.name,
                    result.error,
                )
                self._publish(
                    WorkflowFailed(
                        workflow_id=workflow.workflow_id,
                        name=definition.name,
                        error=workflow_result.error or "",
                        stopped_at=step.name,
                    )
                )
                self._remember(workflow, workflow_result, context)
                return workflow_result

        workflow_result = WorkflowResult(success=True, step_results=dict(step_results))
        logger.info(
            "Workflow %r (%r) completed: %d step(s).",
            workflow.workflow_id,
            definition.name,
            len(step_results),
        )
        self._publish(
            WorkflowCompleted(
                workflow_id=workflow.workflow_id,
                name=definition.name,
                step_count=len(step_results),
            )
        )
        self._remember(workflow, workflow_result, context)
        return workflow_result

    def _publish(self, event: Event) -> None:
        """Publish ``event`` if an :class:`~mellivor_kernel.events.bus.EventBus` is configured."""
        if self._event_bus is not None:
            self._event_bus.publish(event)

    def _remember(
        self, workflow: Workflow, result: WorkflowResult, context: WorkflowContext
    ) -> None:
        """Record ``result`` to memory if a
        :class:`~mellivor_kernel.memory.store.MemoryStore` is configured.

        Never raises: a memory backend failure is logged and swallowed
        rather than allowed to break the workflow.
        """
        if self._memory is None:
            return

        if result.success:
            content = (
                f"Workflow {workflow.definition.name!r} succeeded "
                f"with {len(result.step_results)} step(s)."
            )
        else:
            content = f"Workflow {workflow.definition.name!r} failed: {result.error}"

        entry = MemoryEntry(
            id=workflow.workflow_id,
            content=content,
            tags=frozenset({"workflow"}),
            metadata={
                "name": workflow.definition.name,
                "success": result.success,
                "step_count": len(result.step_results),
            },
        )
        try:
            self._memory.add(entry)
        except Exception as exc:
            context.execution_context.logger.warning(
                "Failed to record workflow %r to memory: %s", workflow.workflow_id, exc
            )
