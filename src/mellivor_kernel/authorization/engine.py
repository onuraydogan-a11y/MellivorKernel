"""AuthorizationEngine: decides whether an operation is authorized."""

from __future__ import annotations

from mellivor_kernel.authorization.permission_set import PermissionSet
from mellivor_kernel.authorization.request import AuthorizationRequest
from mellivor_kernel.authorization.resolver import PermissionResolver
from mellivor_kernel.authorization.result import AuthorizationResult
from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.request import ExecutionRequest
from mellivor_kernel.tools.exceptions import ToolValidationError
from mellivor_kernel.tools.permissions import Permission, missing_permissions


class AuthorizationEngine:
    """Decides whether an operation is authorized. Never executes or dispatches.

    Exposes two methods:

    - :meth:`authorize` -- the core decision: given an
      :class:`AuthorizationRequest`, compare its claimed permissions
      against what :class:`PermissionResolver` says is required, using the
      kernel's existing permission model
      (:func:`~mellivor_kernel.tools.permissions.missing_permissions`). No
      new permission vocabulary or business policy is introduced.
    - :meth:`check` -- the adapter
      :class:`~mellivor_kernel.execution.engine.ExecutionEngine` actually
      calls, satisfying
      :class:`~mellivor_kernel.execution.contracts.Authorizer` structurally.
      It translates an ``ExecutionRequest`` into an
      ``AuthorizationRequest`` and delegates to :meth:`authorize`.
    """

    def __init__(self, permission_resolver: PermissionResolver) -> None:
        """Initialize the engine.

        Args:
            permission_resolver: Determines the permissions required for a
                given target/operation.
        """
        self._permission_resolver = permission_resolver

    def authorize(self, request: AuthorizationRequest) -> AuthorizationResult:
        """Decide whether ``request`` is authorized.

        Args:
            request: The request to authorize.

        Returns:
            A granted :class:`AuthorizationResult` if ``request.granted_permissions``
            covers every permission :class:`PermissionResolver` reports as
            required for ``request.target``/``request.operation``.
            Otherwise a denied result naming the missing permissions.
        """
        required = self._permission_resolver.resolve_required_permissions(
            request.target, request.operation
        )
        missing = missing_permissions(required.permissions, request.granted_permissions.permissions)

        if missing:
            denied = ", ".join(sorted(permission.value for permission in missing))
            return AuthorizationResult(
                granted=False, reason=f"Missing required permissions: {denied}."
            )

        return AuthorizationResult(granted=True, granted_permissions=request.granted_permissions)

    def check(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str],
    ) -> AuthorizationResult:
        """Authorize an ``ExecutionRequest`` on behalf of ``ExecutionEngine``.

        Satisfies :class:`~mellivor_kernel.execution.contracts.Authorizer`
        structurally -- this is the method ``ExecutionEngine`` calls, and
        the only place in this subsystem that touches ``execution`` types.

        Args:
            request: The execution request being authorized.
            context: The execution-lifetime context, used only for logging.
            granted_permissions: The permission identifiers (as raw
                strings) the caller claims to hold for this request.

        Returns:
            A denied :class:`AuthorizationResult` if any claimed
            permission identifier is malformed (see
            :class:`~mellivor_kernel.tools.permissions.Permission`).
            Otherwise, the result of :meth:`authorize`.
        """
        try:
            claimed = PermissionSet(frozenset(Permission(value) for value in granted_permissions))
        except ToolValidationError as exc:
            return AuthorizationResult(granted=False, reason=str(exc))

        result = self.authorize(
            AuthorizationRequest(
                target=request.target, operation=request.operation, granted_permissions=claimed
            )
        )

        if result.granted:
            context.logger.debug(
                "Request %r authorized (target=%s, operation=%r).",
                request.request_id,
                request.target.value,
                request.operation,
            )
        else:
            context.logger.warning(
                "Request %r denied authorization: %s", request.request_id, result.reason
            )

        return result
