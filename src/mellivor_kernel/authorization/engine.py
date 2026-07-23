"""AuthorizationEngine: decides whether an operation is authorized."""

from __future__ import annotations

from mellivor_kernel.authorization.events import AuthorizationDenied, AuthorizationGranted
from mellivor_kernel.authorization.permission_set import PermissionSet
from mellivor_kernel.authorization.request import AuthorizationRequest
from mellivor_kernel.authorization.resolver import PermissionResolver
from mellivor_kernel.authorization.result import AuthorizationResult
from mellivor_kernel.events import Event, EventBus
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
      new permission vocabulary or business policy is introduced. A pure
      decision function -- it never publishes events, since it has no
      execution request id to correlate them with.
    - :meth:`check` -- the adapter
      :class:`~mellivor_kernel.execution.engine.ExecutionEngine` actually
      calls, satisfying
      :class:`~mellivor_kernel.execution.contracts.Authorizer` structurally.
      It translates an ``ExecutionRequest`` into an
      ``AuthorizationRequest``, delegates to :meth:`authorize`, and
      publishes :class:`~mellivor_kernel.authorization.events.AuthorizationGranted`
      or :class:`~mellivor_kernel.authorization.events.AuthorizationDenied`
      when an :class:`~mellivor_kernel.events.bus.EventBus` is configured.
    """

    def __init__(
        self, permission_resolver: PermissionResolver, *, event_bus: EventBus | None = None
    ) -> None:
        """Initialize the engine.

        Args:
            permission_resolver: Determines the permissions required for a
                given target/operation.
            event_bus: The bus decision events are published to. If
                ``None`` (the default), no events are published.
        """
        self._permission_resolver = permission_resolver
        self._event_bus = event_bus

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
        the only place in this subsystem that touches ``execution`` types
        or publishes events.

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
            result = AuthorizationResult(granted=False, reason=str(exc))
            self._publish(
                AuthorizationDenied(
                    request_id=request.request_id,
                    target=request.target,
                    operation=request.operation,
                    reason=result.reason or "",
                )
            )
            return result

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
            self._publish(
                AuthorizationGranted(
                    request_id=request.request_id,
                    target=request.target,
                    operation=request.operation,
                    granted_permissions=frozenset(
                        permission.value for permission in result.granted_permissions.permissions
                    ),
                )
            )
        else:
            context.logger.warning(
                "Request %r denied authorization: %s", request.request_id, result.reason
            )
            self._publish(
                AuthorizationDenied(
                    request_id=request.request_id,
                    target=request.target,
                    operation=request.operation,
                    reason=result.reason or "",
                )
            )

        return result

    def _publish(self, event: Event) -> None:
        """Publish ``event`` if an :class:`~mellivor_kernel.events.bus.EventBus` is configured."""
        if self._event_bus is not None:
            self._event_bus.publish(event)
