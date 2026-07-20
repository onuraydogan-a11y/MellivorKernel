"""Tests for mellivor_kernel.providers.configuration."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.providers import ProviderConfiguration, ProviderConfigurationError


def test_minimal_configuration() -> None:
    config = ProviderConfiguration(provider_name="fake")

    assert config.provider_name == "fake"
    assert config.default_model is None
    assert config.api_key is None
    assert config.base_url is None
    assert config.timeout_seconds == 30.0
    assert config.max_retries == 0
    assert dict(config.extra) == {}


def test_configuration_is_immutable() -> None:
    config = ProviderConfiguration(provider_name="fake")

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.provider_name = "other"  # type: ignore[misc]


def test_rejects_empty_provider_name() -> None:
    with pytest.raises(ProviderConfigurationError):
        ProviderConfiguration(provider_name="   ")


def test_rejects_non_positive_timeout() -> None:
    with pytest.raises(ProviderConfigurationError):
        ProviderConfiguration(provider_name="fake", timeout_seconds=0)


def test_rejects_negative_max_retries() -> None:
    with pytest.raises(ProviderConfigurationError):
        ProviderConfiguration(provider_name="fake", max_retries=-1)


def test_accepts_full_configuration() -> None:
    config = ProviderConfiguration(
        provider_name="fake",
        default_model="fake-model-1",
        api_key="secret",
        base_url="https://example.invalid",
        timeout_seconds=5.0,
        max_retries=3,
        extra={"organization": "acme"},
    )

    assert config.default_model == "fake-model-1"
    assert config.api_key == "secret"
    assert config.base_url == "https://example.invalid"
    assert config.timeout_seconds == 5.0
    assert config.max_retries == 3
    assert config.extra["organization"] == "acme"
