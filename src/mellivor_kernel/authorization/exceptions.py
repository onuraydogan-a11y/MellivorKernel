"""Authorization subsystem exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class AuthorizationError(KernelError):
    """Base class for all errors raised by the authorization subsystem.

    Raised only for invalid data (a malformed ``AuthorizationRequest`` or
    ``AuthorizationResult``) -- an authorization *denial* is a normal,
    non-raising outcome, represented as ``AuthorizationResult(granted=False, ...)``.
    """
