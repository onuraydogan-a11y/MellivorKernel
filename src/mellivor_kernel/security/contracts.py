"""Structural contracts for the kernel's security foundation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mellivor_kernel.security.policy import SecurityDecision


@runtime_checkable
class SecurityPolicy(Protocol):
    """A structural contract for security policy evaluation."""

    def evaluate(self, *, subject: str, action: str) -> SecurityDecision:
        """Evaluate a security decision for a subject and action."""
        ...


@runtime_checkable
class SecureConfiguration(Protocol):
    """A structural contract for access to non-secret and secret values."""

    def get_secret(self, key: str) -> object:
        """Return a managed secret by key."""
        ...

    def get_value(self, key: str) -> object:
        """Return a plain configuration value by key."""
        ...
