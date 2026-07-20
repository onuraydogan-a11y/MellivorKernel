"""Tests for mellivor_kernel.core.runtime."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mellivor_kernel.core import Kernel, KernelState, ServiceContainer, StartupError


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def test_initial_state_is_not_started() -> None:
    kernel = Kernel(_FakeSettings())

    assert kernel.state == KernelState.NOT_STARTED
    health = kernel.health()
    assert health.healthy is False
    assert health.state == KernelState.NOT_STARTED


def test_start_transitions_to_running_and_healthy() -> None:
    kernel = Kernel(_FakeSettings())

    kernel.start()

    assert kernel.state == KernelState.RUNNING
    assert kernel.health().healthy is True


def test_start_twice_raises_startup_error() -> None:
    kernel = Kernel(_FakeSettings())
    kernel.start()

    with pytest.raises(StartupError):
        kernel.start()


def test_shutdown_transitions_to_stopped_and_unhealthy() -> None:
    kernel = Kernel(_FakeSettings())
    kernel.start()

    kernel.shutdown()

    assert kernel.state == KernelState.STOPPED
    health = kernel.health()
    assert health.healthy is False
    assert health.state == KernelState.STOPPED


def test_shutdown_when_not_running_is_a_no_op() -> None:
    kernel = Kernel(_FakeSettings())

    kernel.shutdown()

    assert kernel.state == KernelState.NOT_STARTED


def test_kernel_is_restartable_after_shutdown() -> None:
    kernel = Kernel(_FakeSettings())
    kernel.start()
    kernel.shutdown()

    kernel.start()

    assert kernel.state == KernelState.RUNNING


def test_failed_startup_sets_failed_state_and_detail() -> None:
    kernel = Kernel(_FakeSettings(log_level="NOT_A_LEVEL"))

    with pytest.raises(StartupError):
        kernel.start()

    assert kernel.state == KernelState.FAILED
    health = kernel.health()
    assert health.healthy is False
    assert health.detail != ""


def test_kernel_can_be_restarted_after_failure_once_settings_are_fixed() -> None:
    settings = _FakeSettings(log_level="NOT_A_LEVEL")
    kernel = Kernel(settings)

    with pytest.raises(StartupError):
        kernel.start()
    state_after_failure = kernel.state
    assert state_after_failure == KernelState.FAILED

    settings.log_level = "INFO"
    kernel.start()

    state_after_retry = kernel.state
    assert state_after_retry == KernelState.RUNNING


def test_kernel_uses_provided_container() -> None:
    container = ServiceContainer()
    kernel = Kernel(_FakeSettings(), container=container)

    assert kernel.container is container


def test_kernel_creates_default_container_when_none_provided() -> None:
    kernel = Kernel(_FakeSettings())

    assert isinstance(kernel.container, ServiceContainer)
