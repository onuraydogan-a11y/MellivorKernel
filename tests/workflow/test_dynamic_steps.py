"""Tests for dynamic request construction (ADR-0024, Part A)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool
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


def _make_context() -> WorkflowContext:
    settings = _FakeSettings()
    execution_context = ExecutionContext(
        configuration=settings,
        logger=get_logger("test_dynamic_steps"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )
    return WorkflowContext(execution_context=execution_context)


def _make_execution_engine() -> ExecutionEngine:
    tool_registry = ToolRegistry()
    tool_registry.register(EchoTool())
    return ExecutionEngine(Dispatcher(tool_registry, ProviderRegistry()))


def _static_step(
    name: str, *, payload: Mapping[str, object] | None = None, **kwargs: object
) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload=payload or {}
        ),
        **kwargs,  # type: ignore[arg-type]
    )


# -- construction / invariants -------------------------------------------------


def test_step_requires_exactly_one_of_request_or_request_factory() -> None:
    with pytest.raises(WorkflowError):
        WorkflowStep(name="both", request=None, request_factory=None)


def test_step_rejects_both_request_and_request_factory() -> None:
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")
    with pytest.raises(WorkflowError):
        WorkflowStep(name="both", request=request, request_factory=lambda context: request)


def test_dynamic_step_accepts_request_factory_alone() -> None:
    step = WorkflowStep(
        name="dyn",
        request_factory=lambda context: ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo"
        ),
    )
    assert step.request is None
    assert step.request_factory is not None


# -- static workflow unchanged --------------------------------------------------


def test_static_step_still_uses_request_directly() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="static", steps=(_static_step("only", payload={"x": 1}),))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["only"].payload == {"x": 1}


# -- prior-result resolution / multi-step chaining ------------------------------


def test_dynamic_step_reads_a_prior_step_result() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    dynamic_step = WorkflowStep(
        name="second",
        request_factory=lambda context: ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={"from_first": context.step_results["first"].payload},
        ),
    )
    definition = WorkflowDefinition(
        name="chain", steps=(_static_step("first", payload={"n": 1}), dynamic_step)
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["second"].payload == {"from_first": {"n": 1}}


def test_dynamic_step_chains_across_three_steps() -> None:
    engine = WorkflowEngine(_make_execution_engine())

    def build_second(context: WorkflowContext) -> ExecutionRequest:
        first_value = cast(int, context.step_results["first"].payload["n"])  # type: ignore[index]
        return ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload={"n": first_value + 1}
        )

    def build_third(context: WorkflowContext) -> ExecutionRequest:
        second_value = cast(int, context.step_results["second"].payload["n"])  # type: ignore[index]
        return ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload={"n": second_value + 1}
        )

    definition = WorkflowDefinition(
        name="chain3",
        steps=(
            _static_step("first", payload={"n": 1}),
            WorkflowStep(name="second", request_factory=build_second),
            WorkflowStep(name="third", request_factory=build_third),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["second"].payload == {"n": 2}
    assert result.step_results["third"].payload == {"n": 3}


def test_dynamic_result_to_parallel_group_to_downstream_sequential_step() -> None:
    """Integration: dynamic input feeds parallel branches whose stable,
    declared-order results feed one final sequential request.
    """
    engine = WorkflowEngine(_make_execution_engine())

    def parallel_request(label: str) -> Callable[[WorkflowContext], ExecutionRequest]:
        def build(context: WorkflowContext) -> ExecutionRequest:
            seed = context.step_results["seed"].payload["value"]  # type: ignore[index]
            return ExecutionRequest(
                target=ExecutionTarget.TOOL,
                operation="echo",
                payload={"label": label, "value": seed},
            )

        return build

    def build_final(context: WorkflowContext) -> ExecutionRequest:
        return ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={
                "labels": [
                    context.step_results[name].payload["label"]  # type: ignore[index]
                    for name in ("left", "right")
                ]
            },
        )

    definition = WorkflowDefinition(
        name="dynamic-parallel-sequential",
        steps=(
            _static_step("seed", payload={"value": 7}),
            WorkflowStep(
                name="left", request_factory=parallel_request("left"), parallel_group="fanout"
            ),
            WorkflowStep(
                name="right",
                request_factory=parallel_request("right"),
                parallel_group="fanout",
            ),
            WorkflowStep(name="final", request_factory=build_final),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert list(result.step_results) == ["seed", "left", "right", "final"]
    assert result.step_results["final"].payload == {"labels": ["left", "right"]}


# -- missing prior result --------------------------------------------------------


def test_missing_prior_result_fails_the_step_not_the_run() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    dynamic_step = WorkflowStep(
        name="dyn",
        request_factory=lambda context: ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload=dict(context.step_results["nonexistent"].payload or {}),
        ),
    )
    definition = WorkflowDefinition(name="missing-ref", steps=(dynamic_step,))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.stopped_at == "dyn"
    assert result.step_results["dyn"].metadata["stage"] == "dynamic_request"
    assert "nonexistent" in (result.step_results["dyn"].error or "")


# -- failed dependency ------------------------------------------------------------


def test_dynamic_step_can_read_a_failed_prior_steps_result() -> None:
    """A failed step is still recorded in `step_results` -- a dynamic
    step reading it sees the failed `ExecutionResult`, not a missing key.
    """
    engine = WorkflowEngine(_make_execution_engine())
    failing_step = WorkflowStep(
        name="fails",
        request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="does-not-exist"),
        continue_on_failure=True,
    )
    dynamic_step = WorkflowStep(
        name="after",
        request_factory=lambda context: ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={"prior_succeeded": context.step_results["fails"].success},
        ),
    )
    definition = WorkflowDefinition(name="failed-dep", steps=(failing_step, dynamic_step))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["after"].payload == {"prior_succeeded": False}


# -- deterministic request construction ------------------------------------------


def test_request_factory_is_called_exactly_once_per_run() -> None:
    calls: list[int] = []

    def build(context: WorkflowContext) -> ExecutionRequest:
        calls.append(1)
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="once", steps=(WorkflowStep(name="dyn", request_factory=build),)
    )

    engine.run(Workflow(definition=definition), _make_context())

    assert len(calls) == 1


# -- no prior-result mutation ------------------------------------------------------


def test_request_factory_cannot_retroactively_affect_earlier_results() -> None:
    """Mutating the `step_results` mapping inside a factory (a caller
    misuse -- the kernel does not prevent it structurally, see ADR-0024)
    cannot corrupt the workflow's own accumulated state, since each
    `WorkflowContext` snapshot is a distinct `dict` object.
    """

    def misbehaving_build(context: WorkflowContext) -> ExecutionRequest:
        mutable = context.step_results
        if isinstance(mutable, dict):
            mutable["injected"] = context.step_results["first"]
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="no-mutation",
        steps=(
            _static_step("first", payload={"n": 1}),
            WorkflowStep(name="second", request_factory=misbehaving_build),
        ),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert set(result.step_results) == {"first", "second"}
    assert "injected" not in result.step_results


# -- invalid dynamic resolver output -----------------------------------------------


def test_request_factory_returning_the_wrong_type_fails_clearly() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    bad_step = WorkflowStep(name="bad", request_factory=lambda context: "not a request")  # type: ignore[arg-type,return-value]
    definition = WorkflowDefinition(name="bad-output", steps=(bad_step,))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.step_results["bad"].metadata["stage"] == "dynamic_request"
    assert "str" in (result.step_results["bad"].error or "")


def test_request_factory_returning_none_fails_clearly() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    bad_step = WorkflowStep(name="bad", request_factory=lambda context: None)  # type: ignore[arg-type,return-value]
    definition = WorkflowDefinition(name="bad-none", steps=(bad_step,))

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.step_results["bad"].metadata["stage"] == "dynamic_request"


# -- exception translation / boundaries --------------------------------------------


def test_request_factory_raising_a_custom_exception_is_translated() -> None:
    class _CustomError(RuntimeError):
        pass

    def raises(context: WorkflowContext) -> ExecutionRequest:
        raise _CustomError("boom")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="raises", steps=(WorkflowStep(name="dyn", request_factory=raises),)
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert result.step_results["dyn"].metadata["stage"] == "dynamic_request"
    assert "boom" in (result.step_results["dyn"].error or "")


def test_dynamic_request_failure_respects_continue_on_failure() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    failing_dynamic = WorkflowStep(
        name="dyn",
        request_factory=lambda context: (_ for _ in ()).throw(RuntimeError("nope")),
        continue_on_failure=True,
    )
    definition = WorkflowDefinition(
        name="tolerant-dynamic", steps=(failing_dynamic, _static_step("after", payload={"n": 1}))
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is True
    assert result.step_results["dyn"].success is False
    assert result.step_results["after"].success is True


def test_not_before_is_checked_before_request_factory_is_called() -> None:
    from datetime import UTC, datetime, timedelta

    calls: list[int] = []

    def build(context: WorkflowContext) -> ExecutionRequest:
        calls.append(1)
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    future = datetime.now(UTC) + timedelta(days=1)
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="order",
        steps=(WorkflowStep(name="dyn", request_factory=build, not_before=future),),
    )

    result = engine.run(Workflow(definition=definition), _make_context())

    assert result.success is False
    assert calls == []
    assert result.step_results["dyn"].metadata["stage"] == "scheduling"
