"""Provider configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from mellivor_kernel.providers.exceptions import ProviderConfigurationError


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Immutable, validated configuration for a single provider instance.

    Attributes:
        provider_name: The name of the provider type this configuration is
            for (for example ``"openai"``). Used by
            :class:`~mellivor_kernel.providers.factory.ProviderFactory` to
            select which registered provider constructor to use.
        default_model: The model identifier to use when a request does not
            specify one, if applicable.
        api_key: A credential for authenticating with the provider, if
            applicable. Not validated for format or authenticity here.
        base_url: An endpoint override, if applicable.
        timeout_seconds: The request timeout, in seconds. Must be positive.
        max_retries: The number of retries on transient failure. Must be
            non-negative.
        extra: Provider-specific options not covered by the fields above.
    """

    provider_name: str
    default_model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 0
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate field values.

        Raises:
            ProviderConfigurationError: If ``provider_name`` is empty, if
                ``timeout_seconds`` is not positive, or if ``max_retries``
                is negative.
        """
        if not self.provider_name.strip():
            raise ProviderConfigurationError("provider_name must not be empty.")
        if self.timeout_seconds <= 0:
            raise ProviderConfigurationError(
                f"timeout_seconds must be positive, got {self.timeout_seconds!r}."
            )
        if self.max_retries < 0:
            raise ProviderConfigurationError(
                f"max_retries must be non-negative, got {self.max_retries!r}."
            )
