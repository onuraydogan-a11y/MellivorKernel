"""Tests for mellivor_kernel.providers.factory."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderFactory,
    ProviderHealthCheck,
    ProviderRegistrationError,
)


class _FakeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return self.configuration.provider_name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return dict(request)


def test_register_and_create() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("fake", _FakeProvider)

    provider = factory.create(ProviderConfiguration(provider_name="fake"))

    assert isinstance(provider, _FakeProvider)
    assert provider.name == "fake"


def test_register_twice_raises() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("fake", _FakeProvider)

    with pytest.raises(ProviderRegistrationError):
        factory.register_provider_type("fake", _FakeProvider)


def test_create_unregistered_raises() -> None:
    factory = ProviderFactory()

    with pytest.raises(ProviderRegistrationError):
        factory.create(ProviderConfiguration(provider_name="missing"))


def test_is_registered() -> None:
    factory = ProviderFactory()
    assert factory.is_registered("fake") is False

    factory.register_provider_type("fake", _FakeProvider)

    assert factory.is_registered("fake") is True
