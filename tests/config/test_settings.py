"""Tests for mellivor_kernel.config.settings."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.config import ConfigurationError, Environment, KernelConfig, load_config


def test_default_config() -> None:
    config = KernelConfig()

    assert config.environment == Environment.DEVELOPMENT
    assert config.log_level == "INFO"
    assert config.debug is False


def test_config_rejects_invalid_log_level() -> None:
    with pytest.raises(ConfigurationError):
        KernelConfig(log_level="NOPE")


def test_config_is_immutable() -> None:
    config = KernelConfig()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.log_level = "DEBUG"  # type: ignore[misc]


def test_load_config_with_no_overrides_returns_defaults() -> None:
    config = load_config({})

    assert config == KernelConfig()


def test_load_config_reads_environment_variable_case_insensitively() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "Production"})

    assert config.environment == Environment.PRODUCTION


def test_load_config_rejects_invalid_environment_value() -> None:
    with pytest.raises(ConfigurationError):
        load_config({"MELLIVOR_ENVIRONMENT": "staging"})


def test_load_config_normalizes_log_level_case() -> None:
    config = load_config({"MELLIVOR_LOG_LEVEL": "debug"})

    assert config.log_level == "DEBUG"


def test_load_config_rejects_invalid_log_level() -> None:
    with pytest.raises(ConfigurationError):
        load_config({"MELLIVOR_LOG_LEVEL": "NOPE"})


@pytest.mark.parametrize("raw_value", ["1", "true", "True", "yes", "on"])
def test_load_config_parses_truthy_debug_values(raw_value: str) -> None:
    config = load_config({"MELLIVOR_DEBUG": raw_value})

    assert config.debug is True


@pytest.mark.parametrize("raw_value", ["0", "false", "False", "no", "off"])
def test_load_config_parses_falsy_debug_values(raw_value: str) -> None:
    config = load_config({"MELLIVOR_DEBUG": raw_value})

    assert config.debug is False


def test_load_config_rejects_invalid_debug_value() -> None:
    with pytest.raises(ConfigurationError):
        load_config({"MELLIVOR_DEBUG": "maybe"})


def test_load_config_does_not_read_real_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MELLIVOR_LOG_LEVEL", "ERROR")

    config = load_config({})

    assert config.log_level == "INFO"
