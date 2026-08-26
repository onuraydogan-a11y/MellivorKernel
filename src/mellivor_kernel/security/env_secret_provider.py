"""EnvSecretProvider: a SecretProvider backed by process environment variables."""

from __future__ import annotations

import os
import re

from mellivor_kernel.security.exceptions import (
    SecretConfigurationError,
    SecretNotFoundError,
    SecretValueError,
    SecurityError,
)
from mellivor_kernel.security.secrets import Secret

_ENV_VAR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EnvSecretProvider:
    """A read-only :class:`~mellivor_kernel.security.secrets.SecretProvider`
    backed by the calling process's own environment variables.

    Uses only the Python standard library (``os``, ``re``) -- no new
    dependency, mandatory or optional. See
    `ADR-0022 <../../docs/adr/0022-env-secret-provider.md>`_ for the full
    design rationale.

    ``resolve()`` reads ``os.environ`` fresh on every call -- nothing is
    cached, and no resolved value is retained on this instance after
    ``resolve()`` returns. Safe to call concurrently from multiple
    threads: this class holds no mutable state beyond the immutable
    ``prefix`` set at construction.

    An optional ``prefix`` namespaces every lookup: with
    ``prefix="MELLIVOR_"``, ``resolve("api_key")`` reads
    ``os.environ["MELLIVOR_api_key"]`` -- ``name`` is used verbatim after
    the prefix, no case transformation is applied.
    """

    def __init__(self, prefix: str = "") -> None:
        """Initialize the provider.

        Args:
            prefix: Prepended to every ``name`` passed to :meth:`resolve`
                before looking it up in the environment. Defaults to no
                prefix (``name`` is looked up verbatim).
        """
        self._prefix = prefix

    def resolve(self, name: str) -> Secret:
        """Resolve a secret from an environment variable.

        Args:
            name: The secret's name. Combined with this provider's
                ``prefix`` to form the environment variable key.

        Returns:
            The resolved :class:`~mellivor_kernel.security.secrets.Secret`.

        Raises:
            SecretConfigurationError: If ``name`` is blank, or the
                resolved environment variable key is not a valid
                environment-variable identifier.
            SecretNotFoundError: If no environment variable with the
                resolved key is set.
            SecretValueError: If the environment variable is set but its
                value is invalid (for example, empty).
        """
        if not name.strip():
            raise SecretConfigurationError("Secret name must not be blank.")

        env_key = f"{self._prefix}{name}"
        if not _ENV_VAR_NAME_PATTERN.match(env_key):
            raise SecretConfigurationError(
                f"Secret {name!r} resolves to environment variable key {env_key!r}, "
                "which is not a valid environment variable identifier "
                "(expected to match ^[A-Za-z_][A-Za-z0-9_]*$)."
            )

        if env_key not in os.environ:
            raise SecretNotFoundError(
                f"Secret {name!r} is not set (expected environment variable {env_key!r})."
            )

        try:
            return Secret(name=name, value=os.environ[env_key])
        except SecurityError as exc:
            raise SecretValueError(
                f"Secret {name!r} is set via environment variable {env_key!r} "
                f"but its value is invalid: {exc}"
            ) from exc
