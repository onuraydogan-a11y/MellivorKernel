"""Tests for mellivor_kernel.execution.context."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import ExecutionContext


@dataclasses.dataclass
class _FakeSettings:
    log_level: str = "INFO"


def test_context_holds_all_four_fields() -> None:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    logger = get_logger("test_execution_context")
    services = ServiceContainer()

    context = ExecutionContext(
        configuration=settings, logger=logger, runtime=kernel, services=services
    )

    assert context.configuration is settings
    assert context.logger is logger
    assert context.runtime is kernel
    assert context.services is services


def test_context_is_immutable() -> None:
    context = ExecutionContext(
        configuration=_FakeSettings(),
        logger=get_logger("test_execution_context_immutable"),
        runtime=Kernel(_FakeSettings()),
        services=ServiceContainer(),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.services = ServiceContainer()  # type: ignore[misc]
