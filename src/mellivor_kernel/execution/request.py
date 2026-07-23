"""The execution request type: immutable execution metadata."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from mellivor_kernel.execution.exceptions import ExecutionValidationError


class ExecutionTarget(StrEnum):
    """The subsystem an :class:`ExecutionRequest` should be dispatched to."""

    TOOL = "tool"
    PROVIDER = "provider"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """An immutable request to execute a single unit of work.

    Carries only execution metadata -- which subsystem to dispatch to, which
    operation within that subsystem to invoke, and the opaque payload to
    pass through. It carries no business state and no knowledge of how the
    target subsystem interprets ``payload``.

    Attributes:
        target: Which subsystem this request should be dispatched to.
        operation: The identifier of the operation to invoke within
            ``target`` -- a tool id when ``target`` is
            :attr:`ExecutionTarget.TOOL`, a provider name when ``target`` is
            :attr:`ExecutionTarget.PROVIDER`.
        payload: The request payload passed through to the dispatched
            subsystem, unexamined by the execution core itself.
        request_id: A unique identifier for this request, for correlation in
            logs. Auto-generated if not provided.
    """

    target: ExecutionTarget
    operation: str
    payload: Mapping[str, object] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            ExecutionValidationError: If ``operation`` or ``request_id`` is
                blank.
        """
        if not self.operation.strip():
            raise ExecutionValidationError("ExecutionRequest.operation must not be blank.")
        if not self.request_id.strip():
            raise ExecutionValidationError("ExecutionRequest.request_id must not be blank.")
