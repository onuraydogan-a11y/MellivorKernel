"""The tool execution result type."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.tools.exceptions import ToolValidationError


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A strongly typed, self-contained outcome of a single tool execution.

    Every execution -- whether it failed validation, was denied by the
    permission check, executed successfully, or raised -- is represented
    as a ``ToolResult``. The execution pipeline never lets an exception
    stand in for a result; see
    :class:`~mellivor_kernel.tools.pipeline.ToolExecutionPipeline`.

    Attributes:
        success: Whether the execution succeeded.
        payload: The structured output of a successful execution. ``None``
            for a failed execution.
        error: A human-readable failure description. Required
            (non-empty) when ``success`` is ``False``; must be unset on
            success.
        execution_time_seconds: Wall-clock time spent in the tool's own
            ``execute()`` call, in seconds. ``0.0`` if execution never
            started (for example, a validation or permission failure).
        metadata: Additional, execution-specific information (for example
            which pipeline stage failed).
    """

    success: bool
    payload: Mapping[str, object] | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            ToolValidationError: If ``success`` is ``False`` and ``error``
                is not a non-empty string, if ``success`` is ``True`` and
                ``error`` is set, or if ``execution_time_seconds`` is
                negative.
        """
        if not self.success and not (self.error and self.error.strip()):
            raise ToolValidationError(
                "A failed ToolResult must include a non-empty `error` message."
            )
        if self.success and self.error is not None:
            raise ToolValidationError("A successful ToolResult must not set `error`.")
        if self.execution_time_seconds < 0:
            raise ToolValidationError(
                f"execution_time_seconds must be non-negative, got {self.execution_time_seconds!r}."
            )
