"""Tests for mellivor_kernel.config.environment."""

from __future__ import annotations

import pytest

from mellivor_kernel.config import Environment


def test_environment_values() -> None:
    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.TEST.value == "test"
    assert Environment.PRODUCTION.value == "production"


def test_environment_is_a_string_enum() -> None:
    assert isinstance(Environment.DEVELOPMENT, str)


def test_environment_round_trips_from_value() -> None:
    assert Environment("production") is Environment.PRODUCTION


def test_invalid_environment_value_raises_value_error() -> None:
    with pytest.raises(ValueError):
        Environment("staging")
