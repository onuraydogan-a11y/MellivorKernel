"""Tests for mellivor_kernel.tools.builtin.version_tool."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.tools import ToolContext, ToolExecutionPipeline
from mellivor_kernel.tools.builtin import VersionTool
from mellivor_kernel.version import __version__


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context() -> ToolContext:
    settings = _FakeSettings()
    return ToolContext(
        configuration=settings,
        logger=get_logger("test_version_tool"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_version_tool_requires_no_permissions() -> None:
    tool = VersionTool()

    assert tool.permissions == frozenset()


def test_version_tool_reports_kernel_version() -> None:
    tool = VersionTool()
    context = _make_context()

    result = ToolExecutionPipeline().run(tool, context, {})

    assert result.success is True
    assert result.payload == {"version": __version__}
