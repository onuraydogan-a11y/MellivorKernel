"""Tests for mellivor_kernel.security.env_secret_provider."""

from __future__ import annotations

import os

import pytest

from mellivor_kernel.security import (
    EnvSecretProvider,
    Secret,
    SecretConfigurationError,
    SecretNotFoundError,
    SecretProvider,
    SecretProviderRegistry,
    SecretValueError,
    SecurityError,
)

# --- Protocol conformance ----------------------------------------------------


def test_env_secret_provider_satisfies_the_protocol() -> None:
    assert isinstance(EnvSecretProvider(), SecretProvider)


# --- Successful resolution ---------------------------------------------------


def test_resolves_a_present_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "super-secret")
    provider = EnvSecretProvider()

    secret = provider.resolve("API_KEY")

    assert secret.name == "API_KEY"
    assert secret.value == "super-secret"


def test_resolves_using_a_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MELLIVOR_api_key", "prefixed-secret")
    provider = EnvSecretProvider(prefix="MELLIVOR_")

    secret = provider.resolve("api_key")

    assert secret.name == "api_key"
    assert secret.value == "prefixed-secret"


def test_deterministic_repeated_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "stable-value")
    provider = EnvSecretProvider()

    first = provider.resolve("API_KEY")
    second = provider.resolve("API_KEY")

    assert first == second
    assert first.value == second.value == "stable-value"


def test_reflects_live_environment_changes_between_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "first-value")
    provider = EnvSecretProvider()

    first = provider.resolve("API_KEY")
    monkeypatch.setenv("API_KEY", "second-value")
    second = provider.resolve("API_KEY")

    assert first.value == "first-value"
    assert second.value == "second-value"


# --- Isolation between keys --------------------------------------------------


def test_resolving_one_key_does_not_affect_another(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEY_A", "value-a")
    monkeypatch.setenv("KEY_B", "value-b")
    provider = EnvSecretProvider()

    secret_a = provider.resolve("KEY_A")
    secret_b = provider.resolve("KEY_B")

    assert secret_a.value == "value-a"
    assert secret_b.value == "value-b"


def test_two_providers_with_different_prefixes_are_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("A_KEY", "for-a")
    monkeypatch.setenv("B_KEY", "for-b")
    provider_a = EnvSecretProvider(prefix="A_")
    provider_b = EnvSecretProvider(prefix="B_")

    assert provider_a.resolve("KEY").value == "for-a"
    assert provider_b.resolve("KEY").value == "for-b"


# --- Missing variable ---------------------------------------------------------


def test_missing_variable_raises_secret_not_found_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
    provider = EnvSecretProvider()

    with pytest.raises(SecretNotFoundError, match="DOES_NOT_EXIST"):
        provider.resolve("DOES_NOT_EXIST")


# --- Present but empty value --------------------------------------------------


def test_present_but_empty_value_raises_secret_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMPTY_KEY", "")
    provider = EnvSecretProvider()

    with pytest.raises(SecretValueError, match="EMPTY_KEY"):
        provider.resolve("EMPTY_KEY")


def test_missing_and_empty_raise_different_exception_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_KEY", raising=False)
    monkeypatch.setenv("EMPTY_KEY", "")
    provider = EnvSecretProvider()

    with pytest.raises(SecretNotFoundError):
        provider.resolve("MISSING_KEY")
    with pytest.raises(SecretValueError):
        provider.resolve("EMPTY_KEY")


# --- Malformed configuration ---------------------------------------------------


def test_blank_name_raises_secret_configuration_error() -> None:
    provider = EnvSecretProvider()

    with pytest.raises(SecretConfigurationError):
        provider.resolve("   ")


def test_name_with_invalid_characters_raises_secret_configuration_error() -> None:
    provider = EnvSecretProvider()

    with pytest.raises(SecretConfigurationError):
        provider.resolve("bad=name")


def test_prefix_producing_invalid_key_raises_secret_configuration_error() -> None:
    provider = EnvSecretProvider(prefix="bad prefix ")

    with pytest.raises(SecretConfigurationError):
        provider.resolve("key")


# --- Error translation / hierarchy --------------------------------------------


def test_all_failure_modes_are_security_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    provider = EnvSecretProvider()

    assert issubclass(SecretNotFoundError, SecurityError)
    assert issubclass(SecretValueError, SecurityError)
    assert issubclass(SecretConfigurationError, SecurityError)
    with pytest.raises(SecurityError):
        provider.resolve("MISSING")


# --- Value preservation / no accidental mutation ------------------------------


def test_resolve_does_not_mutate_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "unchanged-value")
    provider = EnvSecretProvider()

    provider.resolve("API_KEY")

    assert os.environ["API_KEY"] == "unchanged-value"


def test_resolved_secret_value_matches_environment_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "exact-value-123!@#")
    provider = EnvSecretProvider()

    secret = provider.resolve("API_KEY")

    assert secret.value == "exact-value-123!@#"


# --- Secret redaction / non-exposure ------------------------------------------


def test_resolved_secret_value_never_appears_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "must-not-leak")
    provider = EnvSecretProvider()

    secret = provider.resolve("API_KEY")

    assert "must-not-leak" not in repr(secret)


def test_empty_value_error_message_does_not_leak_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMPTY_KEY", "")
    provider = EnvSecretProvider()

    with pytest.raises(SecretValueError) as exc_info:
        provider.resolve("EMPTY_KEY")

    assert "EMPTY_KEY" in str(exc_info.value)


def test_missing_error_message_does_not_leak_any_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_KEY", raising=False)
    provider = EnvSecretProvider()

    with pytest.raises(SecretNotFoundError) as exc_info:
        provider.resolve("MISSING_KEY")

    assert "MISSING_KEY" in str(exc_info.value)


# --- Compatibility with existing security components --------------------------


def test_registry_falls_through_to_a_second_provider_on_missing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SHARED_KEY", raising=False)
    env_provider = EnvSecretProvider()

    class FallbackProvider:
        def resolve(self, name: str) -> Secret:
            return Secret(name=name, value="from-fallback")

    registry = SecretProviderRegistry()
    registry.register(env_provider)
    registry.register(FallbackProvider())

    resolved = registry.resolve("SHARED_KEY")

    assert resolved.value == "from-fallback"


def test_registry_prefers_the_first_provider_that_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARED_KEY", "from-env")
    env_provider = EnvSecretProvider()

    class FallbackProvider:
        def resolve(self, name: str) -> Secret:
            raise AssertionError("should not be reached")

    registry = SecretProviderRegistry()
    registry.register(env_provider)
    registry.register(FallbackProvider())

    resolved = registry.resolve("SHARED_KEY")

    assert resolved.value == "from-env"


def test_registry_raises_when_no_provider_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOWHERE", raising=False)
    registry = SecretProviderRegistry()
    registry.register(EnvSecretProvider())

    with pytest.raises(SecurityError):
        registry.resolve("NOWHERE")


# --- Boundary cases ------------------------------------------------------------


def test_no_prefix_by_default_matches_the_variable_name_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNPREFIXED_KEY", "value")
    provider = EnvSecretProvider()

    assert provider.resolve("UNPREFIXED_KEY").value == "value"


def test_value_containing_whitespace_is_preserved_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPACED_KEY", "  leading and trailing  ")
    provider = EnvSecretProvider()

    secret = provider.resolve("SPACED_KEY")

    assert secret.value == "  leading and trailing  "
