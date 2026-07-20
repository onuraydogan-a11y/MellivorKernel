"""Tests for mellivor_kernel.providers.registry."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistrationError,
    ProviderRegistry,
)


class _FakeProvider(BaseProvider):
    def __init__(self, configuration: ProviderConfiguration, *, provider_name: str) -> None:
        super().__init__(configuration)
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return dict(request)


def _make_provider(name: str) -> _FakeProvider:
    return _FakeProvider(ProviderConfiguration(provider_name=name), provider_name=name)


def test_register_and_get() -> None:
    registry = ProviderRegistry()
    provider = _make_provider("fake")

    registry.register(provider)

    assert registry.get("fake") is provider


def test_register_twice_raises() -> None:
    registry = ProviderRegistry()
    registry.register(_make_provider("fake"))

    with pytest.raises(ProviderRegistrationError):
        registry.register(_make_provider("fake"))


def test_get_unregistered_raises() -> None:
    registry = ProviderRegistry()

    with pytest.raises(ProviderRegistrationError):
        registry.get("missing")


def test_is_registered() -> None:
    registry = ProviderRegistry()
    assert registry.is_registered("fake") is False

    registry.register(_make_provider("fake"))

    assert registry.is_registered("fake") is True


def test_list_providers() -> None:
    registry = ProviderRegistry()
    registry.register(_make_provider("alpha"))
    registry.register(_make_provider("beta"))

    assert set(registry.list_providers()) == {"alpha", "beta"}
