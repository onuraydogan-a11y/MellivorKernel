"""Provider health check result."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderHealthCheck:
    """A point-in-time health report for a single provider.

    Attributes:
        healthy: Whether the provider is currently considered reachable
            and usable.
        provider_name: The name of the provider this report is for.
        detail: A human-readable explanation, primarily populated when the
            provider is not healthy.
    """

    healthy: bool
    provider_name: str
    detail: str = ""
