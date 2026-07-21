"""Tests for mellivor_kernel.tools.builtin.health_check_tool."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, KernelState, ServiceContainer, get_logger
from mellivor_kernel.tools import ToolContext, ToolExecutionPipeline
from mellivor_kernel.tools.builtin import HealthCheckTool
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context(*, started: bool) -> ToolContext:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    if started:
        kernel.start()
    return ToolContext(
        configuration=settings,
        logger=get_logger("test_health_check_tool"),
        runtime=kernel,
        services=ServiceContainer(),
    )


def test_health_check_tool_requires_kernel_internal_permission() -> None:
    tool = HealthCheckTool()

    assert tool.permissions == frozenset({KERNEL_INTERNAL})


def test_health_check_tool_denied_without_permission() -> None:
    tool = HealthCheckTool()
    context = _make_context(started=True)

    result = ToolExecutionPipeline().run(tool, context, {})

    assert result.success is False
    assert result.metadata["stage"] == "permission_check"


def test_health_check_tool_reports_running_kernel() -> None:
    tool = HealthCheckTool()
    context = _make_context(started=True)

    result = ToolExecutionPipeline().run(
        tool, context, {}, granted_permissions=frozenset({KERNEL_INTERNAL})
    )

    assert result.success is True
    assert result.payload == {"healthy": True, "state": KernelState.RUNNING.value, "detail": ""}


def test_health_check_tool_reports_not_started_kernel() -> None:
    tool = HealthCheckTool()
    context = _make_context(started=False)

    result = ToolExecutionPipeline().run(
        tool, context, {}, granted_permissions=frozenset({KERNEL_INTERNAL})
    )

    assert result.success is True
    assert result.payload is not None
    assert result.payload["healthy"] is False
    assert result.payload["state"] == KernelState.NOT_STARTED.value
