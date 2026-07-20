"""Tests for mellivor_kernel.providers.capabilities."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.providers import ProviderCapabilities


def test_defaults_are_conservative() -> None:
    capabilities = ProviderCapabilities()

    assert capabilities.supports_streaming is False
    assert capabilities.supports_tool_calls is False
    assert capabilities.supports_vision is False
    assert capabilities.supports_embeddings is False
    assert capabilities.max_context_tokens is None


def test_capabilities_are_immutable() -> None:
    capabilities = ProviderCapabilities()

    with pytest.raises(dataclasses.FrozenInstanceError):
        capabilities.supports_streaming = True  # type: ignore[misc]


def test_capabilities_accept_explicit_values() -> None:
    capabilities = ProviderCapabilities(
        supports_streaming=True,
        supports_tool_calls=True,
        supports_vision=True,
        supports_embeddings=True,
        max_context_tokens=128_000,
    )

    assert capabilities.supports_streaming is True
    assert capabilities.supports_tool_calls is True
    assert capabilities.supports_vision is True
    assert capabilities.supports_embeddings is True
    assert capabilities.max_context_tokens == 128_000
