"""Secret abstractions for the kernel's reusable security foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from mellivor_kernel.security.exceptions import SecurityError


@dataclass(frozen=True, slots=True)
class Secret:
    """A named secret value managed by a consuming application or provider."""

    name: str
    value: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise SecurityError("Secret name must not be empty.")
        if not self.value:
            raise SecurityError("Secret value must not be empty.")

    def __repr__(self) -> str:
        return f"Secret(name={self.name!r}, value='***REDACTED***')"


@runtime_checkable
class SecretProvider(Protocol):
    """A structural provider interface for resolving secrets by name."""

    def resolve(self, name: str) -> Secret:
        """Resolve a secret by its name."""
        ...


class SecretProviderRegistry:
    """A tiny registry for secret providers, wired through dependency injection."""

    def __init__(self) -> None:
        self._providers: list[SecretProvider] = []

    def register(self, provider: SecretProvider) -> None:
        """Register a provider to resolve secrets through."""
        self._providers.append(provider)

    def resolve(self, name: str) -> Secret:
        """Resolve a secret through the registered providers."""
        for provider in self._providers:
            try:
                return provider.resolve(name)
            except SecurityError:
                continue
        raise SecurityError(f"Secret {name!r} is not available from any registered provider.")
