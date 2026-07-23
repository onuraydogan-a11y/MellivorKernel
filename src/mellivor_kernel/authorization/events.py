"""Authorization decision events, published by AuthorizationEngine.

These are ``authorization``'s own event types, not part of the generic
``events`` subsystem -- ``events`` stays free of any knowledge of
"authorization" as a concept, per ADR-0008.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.events import Event
from mellivor_kernel.execution.request import ExecutionTarget


@dataclass(frozen=True, slots=True)
class AuthorizationGranted(Event):
    """Published when an authorization decision grants a request.

    Attributes:
        request_id: The authorized execution request's own id, for
            correlation with the corresponding ``execution`` events.
        target: Which subsystem ``operation`` would be dispatched to.
        operation: The tool id or provider name that was authorized.
        granted_permissions: The permission identifiers (as raw strings)
            found sufficient to grant this request.
    """

    request_id: str
    target: ExecutionTarget
    operation: str
    granted_permissions: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class AuthorizationDenied(Event):
    """Published when an authorization decision denies a request.

    Attributes:
        request_id: The denied execution request's own id, for correlation
            with the corresponding ``execution`` events.
        target: Which subsystem ``operation`` would be dispatched to.
        operation: The tool id or provider name that was denied.
        reason: The denial's human-readable description.
    """

    request_id: str
    target: ExecutionTarget
    operation: str
    reason: str
