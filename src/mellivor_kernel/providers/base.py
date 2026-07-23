"""The provider contract every AI model provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.health import ProviderHealthCheck


class BaseProvider(ABC):
    """The contract every AI model provider must implement.

    Concrete providers subclass this class and satisfy its abstract
    members. Per ``docs/adr/0003-repository-boundaries.md``, integrations
    with *infrastructure* providers -- model providers among them -- belong
    under this repository's ``providers`` package (see
    :mod:`mellivor_kernel.providers.claude` for the reference
    implementation); it is business-application integrations (CRM, HRIS,
    and the like) that belong outside this repository, in a consuming
    product.

    The request/response shape :meth:`invoke` accepts and returns is
    intentionally a generic mapping. Formalizing a concrete request and
    response schema is out of scope for this contract and is left for when
    real providers are integrated.
    """

    def __init__(self, configuration: ProviderConfiguration) -> None:
        """Initialize the provider.

        Args:
            configuration: The configuration this provider instance was
                constructed from.
        """
        self._configuration = configuration

    @property
    def configuration(self) -> ProviderConfiguration:
        """The configuration this provider instance was constructed from."""
        return self._configuration

    @property
    @abstractmethod
    def name(self) -> str:
        """A short, unique identifier for this provider, e.g. ``"openai"``."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """The capabilities this provider supports."""
        ...

    @abstractmethod
    def check_health(self) -> ProviderHealthCheck:
        """Check whether this provider is currently reachable and usable.

        Returns:
            A :class:`ProviderHealthCheck` describing the outcome.
        """
        ...

    @abstractmethod
    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Invoke the underlying model.

        Args:
            request: A provider-specific request payload.

        Returns:
            A provider-specific response payload.
        """
        ...
