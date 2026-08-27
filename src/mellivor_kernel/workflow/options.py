"""Additive execution options for Sprint 30 workflow capabilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.workflow.context import WorkflowContext
from mellivor_kernel.workflow.exceptions import WorkflowError

RequestResolver = Callable[[WorkflowContext, ExecutionRequest], ExecutionRequest]


@dataclass(frozen=True, slots=True)
class WorkflowExecutionOptions:
    """Optional metadata applied to one :meth:`WorkflowEngine.run` call.

    Keeping these capabilities outside :class:`WorkflowStep` preserves its
    frozen v1.0 dataclass contract exactly. Every mapping key and every name
    inside ``parallel_groups`` refers to an existing step by name.
    """

    request_resolvers: Mapping[str, RequestResolver] = field(default_factory=dict)
    parallel_groups: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    not_before: Mapping[str, datetime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate option-local invariants.

        Definition-dependent invariants are checked by ``WorkflowEngine``
        when the options are applied to a concrete workflow.
        """
        for step_name, resolver in self.request_resolvers.items():
            _validate_step_name(step_name, "request_resolvers")
            if not callable(resolver):
                raise WorkflowError(
                    f"WorkflowExecutionOptions.request_resolvers[{step_name!r}] must be callable."
                )

        grouped_names: set[str] = set()
        for group in self.parallel_groups:
            if not group:
                raise WorkflowError("WorkflowExecutionOptions.parallel_groups cannot be empty.")
            for step_name in group:
                _validate_step_name(step_name, "parallel_groups")
                if step_name in grouped_names:
                    raise WorkflowError(
                        f"WorkflowExecutionOptions step {step_name!r} cannot appear in "
                        "more than one parallel group."
                    )
                grouped_names.add(step_name)

        for step_name, scheduled_at in self.not_before.items():
            _validate_step_name(step_name, "not_before")
            if scheduled_at.tzinfo is None:
                raise WorkflowError(
                    f"WorkflowExecutionOptions.not_before[{step_name!r}] must be timezone-aware."
                )


def _validate_step_name(step_name: str, field_name: str) -> None:
    if not step_name.strip():
        raise WorkflowError(f"WorkflowExecutionOptions.{field_name} step names cannot be blank.")
