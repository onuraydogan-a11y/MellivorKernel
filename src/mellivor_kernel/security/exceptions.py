"""Security exceptions for the kernel's reusable security foundation."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class SecurityError(KernelError):
    """Base class for all security-related kernel errors."""


class SecureConfigurationError(SecurityError):
    """Raised when a secure configuration cannot be resolved or validated."""


class SecretNotFoundError(SecurityError):
    """Raised when a requested secret does not exist in a provider's source.

    Backend-agnostic: any concrete
    :class:`~mellivor_kernel.security.secrets.SecretProvider` raises this
    for a missing secret, so
    :class:`~mellivor_kernel.security.secrets.SecretProviderRegistry`'s
    fallback chaining (``except SecurityError: continue``) works
    identically regardless of which backend is registered.
    """


class SecretValueError(SecurityError):
    """Raised when a secret's resolved value fails validation.

    Distinct from :class:`SecretNotFoundError`: the secret's source has
    an entry for the requested name, but the value itself is invalid
    (for example, present but empty) -- never includes the invalid value
    itself in its message.
    """


class SecretConfigurationError(SecurityError):
    """Raised when a secret lookup request is itself invalid.

    Distinct from :class:`SecretNotFoundError`: this is a caller/backend
    configuration problem (for example, a blank secret name, or a name
    that cannot resolve to a valid lookup key for the backend in use),
    independent of whether the secret exists.
    """
