"""Constructs provider instances from configuration."""

from __future__ import annotations

from collections.abc import Callable

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderRegistrationError


class ProviderFactory:
    """Constructs :class:`BaseProvider` instances from a
    :class:`ProviderConfiguration`.

    Provider *implementations* (for example a future OpenAI or Anthropic
    adapter) register a constructor here under their provider name; the
    factory itself has no knowledge of, and does not import, any concrete
    provider.
    """

    def __init__(self) -> None:
        """Initialize an empty factory."""
        self._constructors: dict[str, Callable[[ProviderConfiguration], BaseProvider]] = {}

    def register_provider_type(
        self,
        provider_name: str,
        constructor: Callable[[ProviderConfiguration], BaseProvider],
    ) -> None:
        """Register a constructor for a provider type.

        Args:
            provider_name: The provider type name this constructor builds,
                matching :attr:`ProviderConfiguration.provider_name`.
            constructor: A callable that builds a :class:`BaseProvider`
                from a :class:`ProviderConfiguration`.

        Raises:
            ProviderRegistrationError: If ``provider_name`` already has a
                registered constructor.
        """
        if provider_name in self._constructors:
            raise ProviderRegistrationError(
                f"Provider type {provider_name!r} is already registered with the factory."
            )
        self._constructors[provider_name] = constructor

    def create(self, configuration: ProviderConfiguration) -> BaseProvider:
        """Construct a provider instance from ``configuration``.

        Args:
            configuration: The configuration to build a provider from.

        Returns:
            A new :class:`BaseProvider` instance.

        Raises:
            ProviderRegistrationError: If no constructor is registered for
                ``configuration.provider_name``.
        """
        try:
            constructor = self._constructors[configuration.provider_name]
        except KeyError as exc:
            raise ProviderRegistrationError(
                f"No provider type registered for {configuration.provider_name!r}."
            ) from exc
        return constructor(configuration)

    def is_registered(self, provider_name: str) -> bool:
        """Return whether a constructor is registered for ``provider_name``.

        Args:
            provider_name: The provider type name to check.

        Returns:
            ``True`` if a constructor was registered under ``provider_name``
            via :meth:`register_provider_type`, ``False`` otherwise.
        """
        return provider_name in self._constructors
