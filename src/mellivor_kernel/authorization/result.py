"""AuthorizationResult: the outcome of an authorization decision."""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.authorization.exceptions import AuthorizationError
from mellivor_kernel.authorization.permission_set import PermissionSet


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    """The immutable outcome of a single authorization decision.

    Structurally satisfies :class:`~mellivor_kernel.execution.contracts.AuthorizationOutcome`
    (``granted``, ``reason``) so it can be consumed by
    :class:`~mellivor_kernel.execution.engine.ExecutionEngine` without that
    package importing this one.

    Attributes:
        granted: Whether the request is authorized to proceed to dispatch.
        granted_permissions: The permissions found sufficient to grant
            this request. Empty when ``granted`` is ``False``.
        reason: A human-readable denial reason. Required (non-empty) when
            ``granted`` is ``False``; must be unset when ``granted`` is
            ``True``.
    """

    granted: bool
    granted_permissions: PermissionSet = field(default_factory=PermissionSet.empty)
    reason: str | None = None

    def __post_init__(self) -> None:
        """Validate cross-field invariants.

        Raises:
            AuthorizationError: If ``granted`` is ``False`` and ``reason``
                is not a non-empty string, if ``granted`` is ``True`` and
                ``reason`` is set, or if ``granted`` is ``False`` and
                ``granted_permissions`` is non-empty.
        """
        if not self.granted and not (self.reason and self.reason.strip()):
            raise AuthorizationError(
                "A denied AuthorizationResult must include a non-empty `reason`."
            )
        if self.granted and self.reason is not None:
            raise AuthorizationError("A granted AuthorizationResult must not set `reason`.")
        if not self.granted and self.granted_permissions.permissions:
            raise AuthorizationError(
                "A denied AuthorizationResult must not set `granted_permissions`."
            )
