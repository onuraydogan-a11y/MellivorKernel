"""Executable v1.0 WorkflowStep public-contract freeze checks."""

from __future__ import annotations

import dataclasses
import inspect
from typing import get_type_hints

import pytest

from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.workflow import WorkflowStep


def _request() -> ExecutionRequest:
    return ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")


def _operation_for(step: WorkflowStep) -> str:
    """Strict MyPy must continue accepting this v1.0 consumer pattern."""
    return step.request.operation


def test_v1_constructor_signature_is_restored() -> None:
    parameters = inspect.signature(WorkflowStep).parameters

    assert tuple(parameters) == (
        "name",
        "request",
        "granted_permissions",
        "continue_on_failure",
    )
    assert parameters["name"].default is inspect.Parameter.empty
    assert parameters["request"].default is inspect.Parameter.empty
    assert parameters["request"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_v1_request_annotation_is_non_optional_execution_request() -> None:
    assert get_type_hints(WorkflowStep)["request"] is ExecutionRequest


def test_v1_positional_and_keyword_construction_remain_equivalent() -> None:
    request = _request()

    positional = WorkflowStep("step", request, frozenset({"permission"}), True)
    keyword = WorkflowStep(
        name="step",
        request=request,
        granted_permissions=frozenset({"permission"}),
        continue_on_failure=True,
    )

    assert positional == keyword
    assert _operation_for(positional) == "echo"


def test_v1_request_remains_required() -> None:
    with pytest.raises(TypeError):
        WorkflowStep(name="missing")  # type: ignore[call-arg]


def test_v1_dataclass_field_shape_is_exact() -> None:
    fields = dataclasses.fields(WorkflowStep)

    assert tuple(field.name for field in fields) == (
        "name",
        "request",
        "granted_permissions",
        "continue_on_failure",
    )
    assert all(field.compare for field in fields)
    assert all(field.hash is None for field in fields)
    assert WorkflowStep.__hash__ is not None


def test_v1_repr_and_equality_have_no_execution_option_fields() -> None:
    request = _request()
    first = WorkflowStep(name="step", request=request)
    second = WorkflowStep(name="step", request=request)

    assert first == second
    assert "request_factory" not in repr(first)
    assert "parallel_group" not in repr(first)
    assert "not_before" not in repr(first)


def test_v1_asdict_shape_is_unchanged() -> None:
    serialized = dataclasses.asdict(WorkflowStep(name="step", request=_request()))

    assert tuple(serialized) == (
        "name",
        "request",
        "granted_permissions",
        "continue_on_failure",
    )


def test_v1_plain_subclass_inherits_the_restored_constructor() -> None:
    class SpecializedStep(WorkflowStep):
        pass

    step = SpecializedStep("step", _request())

    assert step.request.operation == "echo"
