"""Tests for parallel step execution (ADR-0024, Part B).

A handful of these tests need *some* real elapsed time to observe actual
thread concurrency -- there is no way to prove two OS threads ran
overlapping without it. Where real timing is unavoidable, assertions are
built on synchronization primitives (a counter under a lock, a
`threading.Event`) rather than raw wall-clock timestamp comparisons, to
keep them as deterministic as the underlying scheduler allows -- the
short `time.sleep` calls below are the *stimulus* that creates an
overlap window, never the basis of an assertion by themselves.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionTarget,
)
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import BaseTool, ToolContext, ToolRegistry, ToolResult
from mellivor_kernel.tools.builtin import EchoTool
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowError,
    WorkflowStep,
)


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


class _FailingTool(BaseTool):
    @property
    def id(self) -> str:
        return "always-fails"

    @property
    def name(self) -> str:
        return "Always Fails"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A tool that always fails."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        return ToolResult(success=False, error="this tool always fails")


class _ConcurrencyCountingTool(BaseTool):
    """Records how many overlapping `execute()` calls were ever in
    flight simultaneously (`max_observed`), via a lock-protected counter.
    A brief sleep creates a window in which a genuinely concurrent second
    call has the opportunity to overlap; the assertion itself is on the
    counter, never on elapsed wall-clock time.
    """

    def __init__(self, *, delay: float = 0.05) -> None:
        self._delay = delay
        self._lock = threading.Lock()
        self._current = 0
        self.max_observed = 0

    @property
    def id(self) -> str:
        return "count-concurrency"

    @property
    def name(self) -> str:
        return "Count Concurrency"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Tracks the maximum number of overlapping executions."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        with self._lock:
            self._current += 1
            self.max_observed = max(self.max_observed, self._current)
        time.sleep(self._delay)
        with self._lock:
            self._current -= 1
        return ToolResult(success=True, payload={"tag": request.get("tag")})


def _make_context() -> WorkflowContext:
    settings = _FakeSettings()
    execution_context = ExecutionContext(
        configuration=settings,
        logger=get_logger("test_parallel_execution"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )
    return WorkflowContext(execution_context=execution_context)


def _make_execution_engine(*extra_tools: BaseTool) -> ExecutionEngine:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    tool_registry.register(_FailingTool())
    for tool in extra_tools:
        tool_registry.register(tool)
    return ExecutionEngine(Dispatcher(tool_registry, ProviderRegistry()))


def _echo_step(
    name: str, *, payload: Mapping[str, object] | None = None, **kwargs: object
) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload=payload or {}
        ),
        **kwargs,  # type: ignore[arg-type]
    )


def _counting_step(name: str, tag: str, **kwargs: object) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="count-concurrency", payload={"tag": tag}
        ),
        **kwargs,  # type: ignore[arg-type]
    )


# -- construction / grouping -----------------------------------------------------


def test_definition_rejects_non_contiguous_parallel_group() -> None:
    with pytest.raises(WorkflowError):
        WorkflowDefinition(
            name="split-group",
            steps=(
                _echo_step("a", parallel_group="g"),
                _echo_step("b"),
                _echo_step("c", parallel_group="g"),
            ),
        )


def test_definition_accepts_contiguous_parallel_group() -> None:
    definition = WorkflowDefinition(
        name="ok-group",
        steps=(
            _echo_step("a", parallel_group="g"),
            _echo_step("b", parallel_group="g"),
            _echo_step("c"),
        ),
    )
    assert len(definition.steps) == 3


def test_engine_rejects_non_positive_max_concurrency() -> None:
    with pytest.raises(WorkflowError):
        WorkflowEngine(_make_execution_engine(), max_concurrency=0)


# -- ungrouped steps are unaffected (no thread pool at all) ----------------------


def test_ungrouped_workflow_never_uses_a_worker_thread() -> None:
    main_thread = threading.current_thread()
    observed_threads: list[threading.Thread] = []

    class _RecordingTool(BaseTool):
        @property
        def id(self) -> str:
            return "record-thread"

        @property
        def name(self) -> str:
            return "Record Thread"

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "Records the current thread."

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset()

        def validate(self, request: Mapping[str, object]) -> None:
            return

        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            observed_threads.append(threading.current_thread())
            return ToolResult(success=True)

    engine = WorkflowEngine(_make_execution_engine(_RecordingTool()))
    definition = WorkflowDefinition(
        name="inline",
        steps=(
            WorkflowStep(
                name="a",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="record-thread"),
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert observed_threads == [main_thread]


# -- explicit parallel group / independent steps run concurrently ----------------


def test_independent_steps_in_a_group_execute_concurrently() -> None:
    counter = _ConcurrencyCountingTool(delay=0.08)
    engine = WorkflowEngine(_make_execution_engine(counter))
    definition = WorkflowDefinition(
        name="concurrent",
        steps=(
            _counting_step("a", "a", parallel_group="g"),
            _counting_step("b", "b", parallel_group="g"),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert counter.max_observed == 2


def test_two_ungrouped_steps_never_overlap() -> None:
    """Contrast case: without `parallel_group`, two steps calling the
    same concurrency-counting tool never overlap -- proving the counting
    tool itself is a meaningful signal, not just always reporting 2.
    """
    counter = _ConcurrencyCountingTool(delay=0.02)
    engine = WorkflowEngine(_make_execution_engine(counter))
    definition = WorkflowDefinition(
        name="sequential", steps=(_counting_step("a", "a"), _counting_step("b", "b"))
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert counter.max_observed == 1


# -- dependent steps never race ahead ---------------------------------------------


def test_step_after_a_group_never_starts_before_the_group_finishes() -> None:
    """No sleep needed: `ThreadPoolExecutor.__exit__` (`with ... as
    executor:`) blocks until every submitted task in the group completes
    before the unit's results are folded in and the next unit runs --
    deterministic by construction, not by timing.
    """
    finished = threading.Event()

    class _SetsEventTool(BaseTool):
        @property
        def id(self) -> str:
            return "sets-event"

        @property
        def name(self) -> str:
            return "Sets Event"

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "Sets a threading.Event before returning."

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset()

        def validate(self, request: Mapping[str, object]) -> None:
            return

        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            finished.set()
            return ToolResult(success=True)

    class _ChecksEventTool(BaseTool):
        @property
        def id(self) -> str:
            return "checks-event"

        @property
        def name(self) -> str:
            return "Checks Event"

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "Reports whether the event was already set."

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset()

        def validate(self, request: Mapping[str, object]) -> None:
            return

        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            return ToolResult(success=True, payload={"event_was_set": finished.is_set()})

    engine = WorkflowEngine(_make_execution_engine(_SetsEventTool(), _ChecksEventTool()))
    definition = WorkflowDefinition(
        name="ordered",
        steps=(
            WorkflowStep(
                name="a",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="sets-event"),
                parallel_group="g",
            ),
            WorkflowStep(
                name="after",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="checks-event"),
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["after"].payload == {"event_was_set": True}


# -- deterministic result ordering -------------------------------------------------


def test_group_result_ordering_matches_declared_order_regardless_of_completion_order() -> None:
    """`fast-second` is made to reliably finish before `slow-first`
    (via an event `slow-first` waits on), yet `step_results` still
    reflects declared order.
    """
    second_done = threading.Event()

    class _WaitsForSecond(BaseTool):
        @property
        def id(self) -> str:
            return "waits"

        @property
        def name(self) -> str:
            return "Waits"

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "Waits for the sibling to finish first."

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset()

        def validate(self, request: Mapping[str, object]) -> None:
            return

        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            second_done.wait(timeout=5)
            return ToolResult(success=True)

    class _SignalsThenFinishes(BaseTool):
        @property
        def id(self) -> str:
            return "signals"

        @property
        def name(self) -> str:
            return "Signals"

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "Signals completion immediately."

        @property
        def capabilities(self) -> frozenset[str]:
            return frozenset()

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset()

        def validate(self, request: Mapping[str, object]) -> None:
            return

        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            second_done.set()
            return ToolResult(success=True)

    engine = WorkflowEngine(_make_execution_engine(_WaitsForSecond(), _SignalsThenFinishes()))
    definition = WorkflowDefinition(
        name="ordering",
        steps=(
            WorkflowStep(
                name="slow-first",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="waits"),
                parallel_group="g",
            ),
            WorkflowStep(
                name="fast-second",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="signals"),
                parallel_group="g",
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert list(result.step_results) == ["slow-first", "fast-second"]


# -- one branch failure -------------------------------------------------------------


def test_one_failing_branch_stops_the_workflow_by_default() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="one-fails",
        steps=(
            _echo_step("ok", parallel_group="g"),
            WorkflowStep(
                name="bad",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
                parallel_group="g",
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.stopped_at == "bad"
    assert set(result.step_results) == {"ok", "bad"}


def test_one_failing_branch_with_continue_on_failure_lets_the_workflow_finish() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="one-fails-tolerant",
        steps=(
            _echo_step("ok", parallel_group="g"),
            WorkflowStep(
                name="bad",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
                parallel_group="g",
                continue_on_failure=True,
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["bad"].success is False
    assert result.step_results["ok"].success is True


# -- multiple branch failures --------------------------------------------------------


def test_multiple_failing_branches_report_the_first_declared_as_stopped_at() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="multi-fail",
        steps=(
            WorkflowStep(
                name="bad-1",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
                parallel_group="g",
            ),
            WorkflowStep(
                name="bad-2",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
                parallel_group="g",
            ),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.stopped_at == "bad-1"


def test_multiple_raising_branches_raise_an_exception_group() -> None:
    class _RaisingExecutionEngine(ExecutionEngine):
        def execute(
            self,
            request: ExecutionRequest,
            context: ExecutionContext,
            *,
            granted_permissions: frozenset[str] = frozenset(),
        ) -> ExecutionResult:
            if request.operation in ("boom-1", "boom-2"):
                raise RuntimeError(request.operation)
            return super().execute(request, context, granted_permissions=granted_permissions)

    execution_engine = _RaisingExecutionEngine(Dispatcher(ToolRegistry(), ProviderRegistry()))
    engine = WorkflowEngine(execution_engine)
    definition = WorkflowDefinition(
        name="raising-group",
        steps=(
            WorkflowStep(
                name="a",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="boom-1"),
                parallel_group="g",
            ),
            WorkflowStep(
                name="b",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="boom-2"),
                parallel_group="g",
            ),
        ),
    )

    with pytest.raises(ExceptionGroup) as excinfo:
        engine.run(Workflow(definition=definition), _make_context())
    assert len(excinfo.value.exceptions) == 2


def test_multiple_raising_branches_are_reported_in_declared_order() -> None:
    release_first = threading.Event()

    class _OutOfOrderRaisingEngine(ExecutionEngine):
        def execute(
            self,
            request: ExecutionRequest,
            context: ExecutionContext,
            *,
            granted_permissions: frozenset[str] = frozenset(),
        ) -> ExecutionResult:
            if request.operation == "first-declared":
                release_first.wait(timeout=5)
                raise RuntimeError("first-declared")
            if request.operation == "second-declared":
                release_first.set()
                raise RuntimeError("second-declared")
            return super().execute(request, context, granted_permissions=granted_permissions)

    engine = WorkflowEngine(
        _OutOfOrderRaisingEngine(Dispatcher(ToolRegistry(), ProviderRegistry()))
    )
    definition = WorkflowDefinition(
        name="ordered-errors",
        steps=(
            WorkflowStep(
                name="first",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="first-declared"),
                parallel_group="g",
            ),
            WorkflowStep(
                name="second",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="second-declared"),
                parallel_group="g",
            ),
        ),
    )

    with pytest.raises(ExceptionGroup) as excinfo:
        engine.run(Workflow(definition=definition), _make_context())

    assert [str(exc) for exc in excinfo.value.exceptions] == [
        "first-declared",
        "second-declared",
    ]


def test_single_raising_branch_re_raises_the_original_exception() -> None:
    class _RaisingExecutionEngine(ExecutionEngine):
        def execute(
            self,
            request: ExecutionRequest,
            context: ExecutionContext,
            *,
            granted_permissions: frozenset[str] = frozenset(),
        ) -> ExecutionResult:
            if request.operation == "boom":
                raise RuntimeError("boom")
            return super().execute(request, context, granted_permissions=granted_permissions)

    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    execution_engine = _RaisingExecutionEngine(Dispatcher(tool_registry, ProviderRegistry()))
    engine = WorkflowEngine(execution_engine)
    definition = WorkflowDefinition(
        name="single-raise",
        steps=(
            WorkflowStep(
                name="a",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="boom"),
                parallel_group="g",
            ),
            _echo_step("b", parallel_group="g"),
        ),
    )

    with pytest.raises(RuntimeError, match="boom"):
        engine.run(Workflow(definition=definition), _make_context())


# -- cancellation -----------------------------------------------------------------


def test_stopping_failure_attempts_to_cancel_every_other_sibling_future() -> None:
    """Cancellation of a not-yet-started sibling is best-effort (ADR-0024):
    whether it actually avoids running depends on a genuine race against
    the pool's own worker thread, which this test deliberately does not
    depend on -- asserting on that race's outcome would be flaky.

    What *is* deterministic, and what this test verifies: as soon as a
    stopping failure is observed, `WorkflowEngine` attempts to cancel
    every other future in the group exactly once. `max_concurrency=1`
    guarantees the single failing step ("a") is the first (and, at the
    moment of cancellation, only) completed future -- FIFO with one
    worker -- so which future triggers the cancellation pass is itself
    deterministic, even though whether "b"/"c" ever actually run is not.
    """
    from concurrent.futures import Future
    from unittest.mock import patch

    original_cancel = Future.cancel
    cancelled: list[Future[ExecutionResult]] = []

    def recording_cancel(self: Future[ExecutionResult]) -> bool:
        cancelled.append(self)
        return original_cancel(self)

    engine = WorkflowEngine(_make_execution_engine(), max_concurrency=1)
    definition = WorkflowDefinition(
        name="cancel-attempt",
        steps=(
            WorkflowStep(
                name="a",
                request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="always-fails"),
                parallel_group="g",
            ),
            _echo_step("b", parallel_group="g"),
            _echo_step("c", parallel_group="g"),
        ),
    )

    with patch.object(Future, "cancel", recording_cancel):
        result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.stopped_at == "a"
    assert len(cancelled) == 2


# -- context / result isolation ------------------------------------------------------


def test_siblings_in_a_group_see_the_same_pre_group_context_not_each_other() -> None:
    seen_step_results: dict[str, Mapping[str, object]] = {}

    def make_recorder(step_name: str) -> Callable[[WorkflowContext], ExecutionRequest]:
        def build(context: WorkflowContext) -> ExecutionRequest:
            seen_step_results[step_name] = dict(context.step_results)
            return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

        return build

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="isolation",
        steps=(
            _echo_step("before", payload={"n": 0}),
            WorkflowStep(name="a", request_factory=make_recorder("a"), parallel_group="g"),
            WorkflowStep(name="b", request_factory=make_recorder("b"), parallel_group="g"),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert set(seen_step_results["a"]) == {"before"}
    assert set(seen_step_results["b"]) == {"before"}


# -- concurrency limit ------------------------------------------------------------


def test_max_concurrency_bounds_simultaneous_execution() -> None:
    counter = _ConcurrencyCountingTool(delay=0.05)
    engine = WorkflowEngine(_make_execution_engine(counter), max_concurrency=1)
    definition = WorkflowDefinition(
        name="bounded",
        steps=(
            _counting_step("a", "a", parallel_group="g"),
            _counting_step("b", "b", parallel_group="g"),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert counter.max_observed == 1


# -- mixed sequential + parallel workflow ------------------------------------------


def test_mixed_sequential_and_parallel_workflow() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="mixed",
        steps=(
            _echo_step("seq1", payload={"n": 1}),
            _echo_step("par1", payload={"n": 2}, parallel_group="g"),
            _echo_step("par2", payload={"n": 3}, parallel_group="g"),
            _echo_step("seq2", payload={"n": 4}),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert list(result.step_results) == ["seq1", "par1", "par2", "seq2"]
