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
    WorkflowExecutionOptions,
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


def _static_step(name: str, *, payload: Mapping[str, object] | None = None) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        request=ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload=payload or {}
        ),
    )


# -- construction / invariants -------------------------------------------------


def test_options_reject_a_non_callable_request_resolver() -> None:
    with pytest.raises(WorkflowError, match="must be callable"):
        WorkflowExecutionOptions(request_resolvers={"step": "not callable"})  # type: ignore[dict-item]


def test_options_reject_an_unknown_step_name_when_run() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    workflow = Workflow(definition=WorkflowDefinition(name="empty"))
    options = WorkflowExecutionOptions(
        request_resolvers={"missing": lambda context, request: request}
    )

    with pytest.raises(WorkflowError, match="unknown step"):
        engine.run(workflow, _make_context(), options=options)


def test_dynamic_resolver_uses_the_required_static_request_as_its_base() -> None:
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"base": 1})
    step = WorkflowStep(name="dyn", request=request)
    seen: list[ExecutionRequest] = []

    def resolve(context: WorkflowContext, base: ExecutionRequest) -> ExecutionRequest:
        seen.append(base)
        return base

    result = WorkflowEngine(_make_execution_engine()).run(
        Workflow(definition=WorkflowDefinition(name="dynamic", steps=(step,))),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"dyn": resolve}),
    )

    assert result.success is True
    assert seen == [request]


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
    dynamic_step = _static_step("second")

    def resolver(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        return ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={"from_first": context.step_results["first"].payload},
        )

    definition = WorkflowDefinition(
        name="chain", steps=(_static_step("first", payload={"n": 1}), dynamic_step)
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"second": resolver}),
    )

    assert result.success is True
    assert result.step_results["second"].payload == {"from_first": {"n": 1}}


def test_dynamic_step_chains_across_three_steps() -> None:
    engine = WorkflowEngine(_make_execution_engine())

    def build_second(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        first_value = cast(int, context.step_results["first"].payload["n"])  # type: ignore[index]
        return ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload={"n": first_value + 1}
        )

    def build_third(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        second_value = cast(int, context.step_results["second"].payload["n"])  # type: ignore[index]
        return ExecutionRequest(
            target=ExecutionTarget.TOOL, operation="echo", payload={"n": second_value + 1}
        )

    definition = WorkflowDefinition(
        name="chain3",
        steps=(
            _static_step("first", payload={"n": 1}),
            _static_step("second"),
            _static_step("third"),
        ),
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={"second": build_second, "third": build_third}
        ),
    )

    assert result.success is True
    assert result.step_results["second"].payload == {"n": 2}
    assert result.step_results["third"].payload == {"n": 3}


def test_dynamic_result_to_parallel_group_to_downstream_sequential_step() -> None:
    """Integration: dynamic input feeds parallel branches whose stable,
    declared-order results feed one final sequential request.
    """
    engine = WorkflowEngine(_make_execution_engine())

    def parallel_request(
        label: str,
    ) -> Callable[[WorkflowContext, ExecutionRequest], ExecutionRequest]:
        def build(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
            seed = context.step_results["seed"].payload["value"]  # type: ignore[index]
            return ExecutionRequest(
                target=ExecutionTarget.TOOL,
                operation="echo",
                payload={"label": label, "value": seed},
            )

        return build

    def build_final(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
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
            _static_step("left"),
            _static_step("right"),
            _static_step("final"),
        ),
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={
                "left": parallel_request("left"),
                "right": parallel_request("right"),
                "final": build_final,
            },
            parallel_groups=(("left", "right"),),
        ),
    )

    assert result.success is True
    assert list(result.step_results) == ["seed", "left", "right", "final"]
    assert result.step_results["final"].payload == {"labels": ["left", "right"]}


# -- missing prior result --------------------------------------------------------


def test_missing_prior_result_fails_the_step_not_the_run() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    dynamic_step = _static_step("dyn")

    def resolver(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        return ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload=dict(context.step_results["nonexistent"].payload or {}),
        )

    definition = WorkflowDefinition(name="missing-ref", steps=(dynamic_step,))

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"dyn": resolver}),
    )

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
    dynamic_step = _static_step("after")

    def resolver(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        return ExecutionRequest(
            target=ExecutionTarget.TOOL,
            operation="echo",
            payload={"prior_succeeded": context.step_results["fails"].success},
        )

    definition = WorkflowDefinition(name="failed-dep", steps=(failing_step, dynamic_step))

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"after": resolver}),
    )

    assert result.success is True
    assert result.step_results["after"].payload == {"prior_succeeded": False}


# -- deterministic request construction ------------------------------------------


def test_request_resolver_is_called_exactly_once_per_run() -> None:
    calls: list[int] = []

    def build(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        calls.append(1)
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="once", steps=(_static_step("dyn"),))

    engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"dyn": build}),
    )

    assert len(calls) == 1


# -- no prior-result mutation ------------------------------------------------------


def test_request_resolver_cannot_retroactively_affect_earlier_results() -> None:
    """Mutating the `step_results` mapping inside a factory (a caller
    misuse -- the kernel does not prevent it structurally, see ADR-0024)
    cannot corrupt the workflow's own accumulated state, since each
    `WorkflowContext` snapshot is a distinct `dict` object.
    """

    def misbehaving_build(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        mutable = context.step_results
        if isinstance(mutable, dict):
            mutable["injected"] = context.step_results["first"]
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="no-mutation",
        steps=(
            _static_step("first", payload={"n": 1}),
            _static_step("second"),
        ),
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"second": misbehaving_build}),
    )

    assert result.success is True
    assert set(result.step_results) == {"first", "second"}
    assert "injected" not in result.step_results


# -- invalid dynamic resolver output -----------------------------------------------


def test_request_resolver_returning_the_wrong_type_fails_clearly() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    bad_step = _static_step("bad")
    definition = WorkflowDefinition(name="bad-output", steps=(bad_step,))

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={"bad": lambda context, request: "not a request"}  # type: ignore[dict-item,return-value]
        ),
    )

    assert result.success is False
    assert result.step_results["bad"].metadata["stage"] == "dynamic_request"
    assert "str" in (result.step_results["bad"].error or "")


def test_request_resolver_returning_none_fails_clearly() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    bad_step = _static_step("bad")
    definition = WorkflowDefinition(name="bad-none", steps=(bad_step,))

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={"bad": lambda context, request: None}  # type: ignore[dict-item,return-value]
        ),
    )

    assert result.success is False
    assert result.step_results["bad"].metadata["stage"] == "dynamic_request"


# -- exception translation / boundaries --------------------------------------------


def test_request_resolver_raising_a_custom_exception_is_translated() -> None:
    class _CustomError(RuntimeError):
        pass

    def raises(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        raise _CustomError("boom")

    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(name="raises", steps=(_static_step("dyn"),))

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(request_resolvers={"dyn": raises}),
    )

    assert result.success is False
    assert result.step_results["dyn"].metadata["stage"] == "dynamic_request"
    assert "boom" in (result.step_results["dyn"].error or "")


def test_dynamic_request_failure_respects_continue_on_failure() -> None:
    engine = WorkflowEngine(_make_execution_engine())
    failing_dynamic = WorkflowStep(
        name="dyn",
        request=ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"),
        continue_on_failure=True,
    )
    definition = WorkflowDefinition(
        name="tolerant-dynamic", steps=(failing_dynamic, _static_step("after", payload={"n": 1}))
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={
                "dyn": lambda context, request: (_ for _ in ()).throw(RuntimeError("nope"))
            }
        ),
    )

    assert result.success is True
    assert result.step_results["dyn"].success is False
    assert result.step_results["after"].success is True


def test_not_before_is_checked_before_request_resolver_is_called() -> None:
    from datetime import UTC, datetime, timedelta

    calls: list[int] = []

    def build(context: WorkflowContext, request: ExecutionRequest) -> ExecutionRequest:
        calls.append(1)
        return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    future = datetime.now(UTC) + timedelta(days=1)
    engine = WorkflowEngine(_make_execution_engine())
    definition = WorkflowDefinition(
        name="order",
        steps=(_static_step("dyn"),),
    )

    result = engine.run(
        Workflow(definition=definition),
        _make_context(),
        options=WorkflowExecutionOptions(
            request_resolvers={"dyn": build}, not_before={"dyn": future}
        ),
    )

    assert result.success is False
    assert calls == []
    assert result.step_results["dyn"].metadata["stage"] == "scheduling"
