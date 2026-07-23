"""The common execution result type."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.execution.exceptions import ExecutionValidationError


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """A strongly typed, self-contained outcome of a single execution.

    Every dispatched execution -- whether it failed validation, failed to
    resolve its target, executed successfully, or raised -- is represented
    as an ``ExecutionResult``. Deliberately generic so it is reusable as the
    outcome type for tool, provider, workflow, and agent execution alike,
    rather than each future subsystem inventing its own result shape.

    Attributes:
        success: Whether the execution succeeded.
        payload: The structured output of a successful execution. ``None``
            for a failed execution.
        error: A human-readable failure description. Required (non-empty)
            when ``success`` is ``False``; must be unset on success.
        execution_time_seconds: Wall-clock time spent executing, in
            seconds. ``0.0`` if execution never started (for example, a
            dispatch failure).
        metadata: Additional, execution-specific information (for example
            which target the request was dispatched to).
    """

    success: bool
    payload: Mapping[str, object] | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            ExecutionValidationError: If ``success`` is ``False`` and
                ``error`` is not a non-empty string, if ``success`` is
                ``True`` and ``error`` is set, or if
                ``execution_time_seconds`` is negative.
        """
        if not self.success and not (self.error and self.error.strip()):
            raise ExecutionValidationError(
                "A failed ExecutionResult must include a non-empty `error` message."
            )
        if self.success and self.error is not None:
            raise ExecutionValidationError("A successful ExecutionResult must not set `error`.")
        if self.execution_time_seconds < 0:
            raise ExecutionValidationError(
                f"execution_time_seconds must be non-negative, got {self.execution_time_seconds!r}."
            )
