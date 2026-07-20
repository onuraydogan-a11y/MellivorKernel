"""A registry of configured provider instances, keyed by provider name."""

from __future__ import annotations

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.exceptions import ProviderRegistrationError


class ProviderRegistry:
    """A registry of constructed :class:`BaseProvider` instances, keyed by
    each provider's own :attr:`~BaseProvider.name`.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance under its own ``name``.

        Args:
            provider: The provider instance to register.

        Raises:
            ProviderRegistrationError: If a provider is already registered
                under ``provider.name``.
        """
        name = provider.name
        if name in self._providers:
            raise ProviderRegistrationError(f"Provider {name!r} is already registered.")
        self._providers[name] = provider

    def get(self, name: str) -> BaseProvider:
        """Resolve a registered provider by name.

        Args:
            name: The provider name to look up.

        Returns:
            The registered provider instance.

        Raises:
            ProviderRegistrationError: If no provider is registered under
                ``name``.
        """
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ProviderRegistrationError(f"Provider {name!r} is not registered.") from exc

    def is_registered(self, name: str) -> bool:
        """Return whether a provider is registered under ``name``.

        Args:
            name: The provider name to check.

        Returns:
            ``True`` if a provider was registered under ``name`` via
            :meth:`register`, ``False`` otherwise.
        """
        return name in self._providers

    def list_providers(self) -> tuple[str, ...]:
        """Return the names of all currently registered providers.

        Returns:
            A tuple of provider names, in registration order.
        """
        return tuple(self._providers)
