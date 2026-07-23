"""Public API of the kernel's authorization subsystem.

Decides whether an :class:`~mellivor_kernel.execution.request.ExecutionRequest`
is authorized to proceed to dispatch -- nothing more. This subsystem never
executes, never dispatches, and never contains business logic; it compares
claimed permissions against declared requirements using the kernel's
existing permission model (:mod:`mellivor_kernel.tools.permissions`), no
new permission vocabulary invented.

``execution`` never imports this package -- see
:mod:`mellivor_kernel.execution.contracts` and ADR-0007 for the structural
seam (``Authorizer``/``AuthorizationOutcome``) that lets
:class:`AuthorizationEngine` be consumed by
:class:`~mellivor_kernel.execution.engine.ExecutionEngine` without that
dependency ever existing.
"""

from __future__ import annotations

from mellivor_kernel.authorization.engine import AuthorizationEngine
from mellivor_kernel.authorization.exceptions import AuthorizationError
from mellivor_kernel.authorization.permission_set import PermissionSet
from mellivor_kernel.authorization.request import AuthorizationRequest
from mellivor_kernel.authorization.resolver import PermissionResolver
from mellivor_kernel.authorization.result import AuthorizationResult

__all__ = [
    "AuthorizationEngine",
    "AuthorizationError",
    "AuthorizationRequest",
    "AuthorizationResult",
    "PermissionResolver",
    "PermissionSet",
]
