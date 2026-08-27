"""WorkflowEngine: orchestrates execution of a workflow's steps.

Steps run strictly in the order their execution *units* appear in
``definition.steps`` -- a unit is either a single, ungrouped step (run
inline, in the calling thread, exactly as before Sprint 30) or a
contiguous run of steps sharing the same
:attr:`~mellivor_kernel.workflow.step.WorkflowStep.parallel_group` (run
concurrently, via a `ThreadPoolExecutor` scoped to that one unit). See
`ADR-0024 <../../docs/adr/0024-workflow-dynamic-parallel-scheduled-steps.md>`_
for the full design: dynamic request construction, parallel execution,
and scheduling guards.
"""

from __future__ import annotations

import dataclasses
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from mellivor_kernel.events import Event, EventBus
from mellivor_kernel.execution.engine import ExecutionEngine
from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.execution.result import ExecutionResult
from mellivor_kernel.memory import MemoryEntry, MemoryStore
from mellivor_kernel.workflow.clock import Clock, SystemClock
from mellivor_kernel.workflow.context import WorkflowContext
from mellivor_kernel.workflow.events import WorkflowCompleted, WorkflowFailed, WorkflowStarted
from mellivor_kernel.workflow.exceptions import WorkflowError
from mellivor_kernel.workflow.result import WorkflowResult
from mellivor_kernel.workflow.step import WorkflowStep
from mellivor_kernel.workflow.workflow import Workflow


class WorkflowEngine:
    """Orchestrates execution of a :class:`Workflow`'s steps.

    Never executes a tool or provider directly, and never performs a
    provider call itself -- every step is delegated to the injected
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine`, the
    kernel's single execution entry point. ``WorkflowEngine`` composes
    calls to it; it does not duplicate, bypass, or reimplement any part
    of what ``ExecutionEngine`` already does (authorization, dispatch,
    event publication, memory recording at the execution level).

    Steps run strictly in the order their execution units appear in
    ``definition.steps``. A step whose
    :attr:`~mellivor_kernel.workflow.step.WorkflowStep.parallel_group` is
    unset (the default) runs on its own, inline, in the calling thread --
    no concurrency is introduced unless a workflow explicitly opts in via
    ``parallel_group``. A step's failure stops the workflow unless that
    step sets :attr:`~mellivor_kernel.workflow.step.WorkflowStep.continue_on_failure`.
    """

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        *,
        memory: MemoryStore | None = None,
        event_bus: EventBus | None = None,
        max_concurrency: int | None = None,
        clock: Clock | None = None,
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
            max_concurrency: The maximum number of steps run concurrently
                within any one parallel unit. ``None`` (the default)
                means unbounded -- every step in a unit is submitted at
                once. Has no effect on ungrouped steps, which never use a
                thread pool. See ADR-0024's "Thread/async safety
                assumptions" before combining this with a shared,
                non-thread-safe ``MemoryStore`` (for example
                ``SQLiteMemoryStore``) on ``execution_engine``.
            clock: The time source :attr:`~mellivor_kernel.workflow.step.WorkflowStep.not_before`
                is evaluated against. A real :class:`~mellivor_kernel.workflow.clock.SystemClock`
                is constructed here, at object-construction time, if none
                is given -- never a module-level or import-time default.

        Raises:
            WorkflowError: If ``max_concurrency`` is given and not
                positive.
        """
        if max_concurrency is not None and max_concurrency <= 0:
            raise WorkflowError(
                f"max_concurrency must be positive if given, got {max_concurrency!r}."
            )
        self._execution_engine = execution_engine
        self._memory = memory
        self._event_bus = event_bus
        self._max_concurrency = max_concurrency
        self._clock: Clock = clock if clock is not None else SystemClock()

    def run(self, workflow: Workflow, context: WorkflowContext) -> WorkflowResult:
        """Run every step of ``workflow.definition``, in order.

        Args:
            workflow: The workflow run to execute.
            context: The shared context to run with.

        Returns:
            A :class:`WorkflowResult`. ``success`` is ``True`` unless a
            step fails without ``continue_on_failure``, in which case the
            workflow stops before running any further unit.
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
        for unit in _group_into_units(definition.steps):
            unit_results = self._run_unit(unit, running_context)

            step_results.update(unit_results)
            running_context = dataclasses.replace(running_context, step_results=dict(step_results))

            stopping = _first_stopping_failure(unit, unit_results)
            if stopping is not None:
                stopping_step, stopping_result = stopping
                workflow_result = WorkflowResult(
                    success=False,
                    step_results=dict(step_results),
                    error=f"Step {stopping_step.name!r} failed: {stopping_result.error}",
                    stopped_at=stopping_step.name,
                )
                logger.warning(
                    "Workflow %r stopped at step %r: %s",
                    workflow.workflow_id,
                    stopping_step.name,
                    stopping_result.error,
                )
                self._publish(
                    WorkflowFailed(
                        workflow_id=workflow.workflow_id,
                        name=definition.name,
                        error=workflow_result.error or "",
                        stopped_at=stopping_step.name,
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

    def _run_unit(
        self, unit: list[WorkflowStep], context: WorkflowContext
    ) -> dict[str, ExecutionResult]:
        """Run one execution unit and return its results, keyed by step name.

        A unit of exactly one ungrouped step runs inline, in the calling
        thread -- no thread pool is used. A unit with a
        ``parallel_group`` set runs every step concurrently.
        """
        if len(unit) == 1 and unit[0].parallel_group is None:
            step = unit[0]
            return {step.name: self._resolve_and_execute_step(step, context)}
        return self._run_parallel_group(unit, context)

    def _run_parallel_group(
        self, group: list[WorkflowStep], context: WorkflowContext
    ) -> dict[str, ExecutionResult]:
        """Run every step of ``group`` concurrently, in a thread pool
        scoped to this call, and return its results in declared order.

        Raises:
            BaseException: The exception a single raising step raised, or
                (if more than one step raised) an ``ExceptionGroup``
                wrapping every raised exception, in declared order --
                mirroring exactly how a single, sequential step's own
                unexpected exception already propagates out of
                :meth:`run` uncaught.
        """
        max_workers = self._max_concurrency if self._max_concurrency is not None else len(group)
        completed: dict[str, ExecutionResult] = {}
        raised: dict[str, Exception] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_step: dict[Future[ExecutionResult], WorkflowStep] = {
                executor.submit(self._resolve_and_execute_step, step, context): step
                for step in group
            }
            stopped = False
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                if future.cancelled():
                    continue
                try:
                    result = future.result()
                except Exception as exc:  # re-raised/aggregated below, never swallowed
                    raised[step.name] = exc
                    continue
                completed[step.name] = result
                if not stopped and not result.success and not step.continue_on_failure:
                    stopped = True
                    for other_future in future_to_step:
                        if other_future is not future:
                            other_future.cancel()

        if raised:
            declared_order = [raised[step.name] for step in group if step.name in raised]
            if len(declared_order) == 1:
                raise declared_order[0]
            raise ExceptionGroup(
                f"{len(declared_order)} step(s) in a parallel group raised.", declared_order
            )

        return {step.name: completed[step.name] for step in group if step.name in completed}

    def _resolve_and_execute_step(
        self, step: WorkflowStep, context: WorkflowContext
    ) -> ExecutionResult:
        """Resolve ``step``'s request (static or dynamic), honor its
        scheduling guard, and execute it -- the per-step pipeline shared
        by both the inline and the parallel-unit execution paths.
        """
        now = self._clock.now()
        if step.not_before is not None and now < step.not_before:
            return ExecutionResult(
                success=False,
                error=(
                    f"Step {step.name!r} is not yet due to run "
                    f"(not_before={step.not_before.isoformat()}, now={now.isoformat()})."
                ),
                metadata={"stage": "scheduling"},
            )

        if step.request_factory is not None:
            try:
                candidate = step.request_factory(context)
            except Exception as exc:
                return ExecutionResult(
                    success=False,
                    error=f"Dynamic request construction failed for step {step.name!r}: {exc}",
                    metadata={"stage": "dynamic_request"},
                )
            if not isinstance(candidate, ExecutionRequest):
                return ExecutionResult(
                    success=False,
                    error=(
                        f"Step {step.name!r}'s request_factory returned "
                        f"{type(candidate).__name__}, expected ExecutionRequest."
                    ),
                    metadata={"stage": "dynamic_request"},
                )
            request = candidate
        else:
            assert step.request is not None  # enforced by WorkflowStep.__post_init__
            request = step.request

        return self._execution_engine.execute(
            request, context.execution_context, granted_permissions=step.granted_permissions
        )

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


def _group_into_units(steps: tuple[WorkflowStep, ...]) -> list[list[WorkflowStep]]:
    """Partition ``steps`` into execution units: a maximal run of 1+
    steps sharing the same non-``None`` ``parallel_group``, or a single
    ungrouped step.

    Relies on :class:`~mellivor_kernel.workflow.definition.WorkflowDefinition`
    already having validated that a given ``parallel_group`` value's
    steps are contiguous, so a group name is never split across two
    units here.
    """
    units: list[list[WorkflowStep]] = []
    for step in steps:
        if (
            step.parallel_group is not None
            and units
            and units[-1][0].parallel_group == step.parallel_group
        ):
            units[-1].append(step)
        else:
            units.append([step])
    return units


def _first_stopping_failure(
    unit: list[WorkflowStep], unit_results: dict[str, ExecutionResult]
) -> tuple[WorkflowStep, ExecutionResult] | None:
    """Return the first step (in ``unit``'s declared order) whose result
    failed without ``continue_on_failure``, or ``None`` if none did.
    """
    for step in unit:
        result = unit_results.get(step.name)
        if result is not None and not result.success and not step.continue_on_failure:
            return step, result
    return None
