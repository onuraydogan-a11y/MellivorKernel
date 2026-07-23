"""Structural contracts execution depends on to check authorization,
without depending on how that decision is made.

Mirrors :mod:`mellivor_kernel.core.contracts`: ``core`` depends on the
*shape* of configuration (``KernelSettings``) without importing ``config``;
here, ``execution`` depends on the *shape* of an authorization decision
without importing ``authorization``. Any object satisfying these Protocols
structurally -- most notably
:class:`~mellivor_kernel.authorization.engine.AuthorizationEngine` -- can be
handed to :class:`~mellivor_kernel.execution.engine.ExecutionEngine`
without ``execution`` ever importing the ``authorization`` package.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.request import ExecutionRequest


@runtime_checkable
class AuthorizationOutcome(Protocol):
    """The subset of an authorization decision execution depends on."""

    @property
    def granted(self) -> bool:
        """Whether the request is authorized to proceed to dispatch."""
        ...

    @property
    def reason(self) -> str | None:
        """A human-readable denial reason. Unset when :attr:`granted` is ``True``."""
        ...


@runtime_checkable
class Authorizer(Protocol):
    """Anything capable of deciding whether an ``ExecutionRequest`` is authorized."""

    def check(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str],
    ) -> AuthorizationOutcome:
        """Decide whether ``request`` is authorized to proceed to dispatch.

        Args:
            request: The request being authorized.
            context: The execution-lifetime context to authorize with.
            granted_permissions: The permission identifiers (as raw strings)
                the caller claims to hold for this request.

        Returns:
            The authorization decision.
        """
        ...
