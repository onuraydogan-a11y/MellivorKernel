"""Tests for mellivor_kernel.providers.base."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
)


class _FakeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "fake"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=True)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echo": request}


def test_base_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseProvider(ProviderConfiguration(provider_name="fake"))  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated() -> None:
    class _Incomplete(BaseProvider):
        @property
        def name(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        _Incomplete(ProviderConfiguration(provider_name="incomplete"))  # type: ignore[abstract]


def test_concrete_provider_exposes_configuration() -> None:
    config = ProviderConfiguration(provider_name="fake")
    provider = _FakeProvider(config)

    assert provider.configuration is config
    assert provider.name == "fake"
    assert provider.capabilities.supports_streaming is True


def test_concrete_provider_health_check() -> None:
    provider = _FakeProvider(ProviderConfiguration(provider_name="fake"))

    report = provider.check_health()

    assert report.healthy is True
    assert report.provider_name == "fake"


def test_concrete_provider_invoke() -> None:
    provider = _FakeProvider(ProviderConfiguration(provider_name="fake"))

    response = provider.invoke({"prompt": "hello"})

    assert response == {"echo": {"prompt": "hello"}}
