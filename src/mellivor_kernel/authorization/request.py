"""AuthorizationRequest: the input to an authorization decision."""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.authorization.exceptions import AuthorizationError
from mellivor_kernel.authorization.permission_set import PermissionSet
from mellivor_kernel.execution.request import ExecutionTarget


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """An immutable request to decide whether an operation is authorized.

    Deliberately independent of :class:`~mellivor_kernel.execution.request.ExecutionRequest`
    beyond sharing the same ``target``/``operation`` vocabulary: this is
    the type :class:`~mellivor_kernel.authorization.engine.AuthorizationEngine`'s
    core decision method operates on, testable without constructing an
    ``ExecutionContext`` or a running kernel.

    Attributes:
        target: Which subsystem ``operation`` would be dispatched to.
        operation: The tool id or provider name being authorized.
        granted_permissions: The permissions the caller claims to hold for
            this request.
    """

    target: ExecutionTarget
    operation: str
    granted_permissions: PermissionSet = field(default_factory=PermissionSet.empty)

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            AuthorizationError: If ``operation`` is blank.
        """
        if not self.operation.strip():
            raise AuthorizationError("AuthorizationRequest.operation must not be blank.")
