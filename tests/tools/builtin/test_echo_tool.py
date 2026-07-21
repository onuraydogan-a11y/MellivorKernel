"""Tests for mellivor_kernel.tools.builtin.echo_tool."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.tools import ToolContext, ToolExecutionPipeline
from mellivor_kernel.tools.builtin import EchoTool


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context() -> ToolContext:
    settings = _FakeSettings()
    return ToolContext(
        configuration=settings,
        logger=get_logger("test_echo_tool"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_echo_tool_metadata() -> None:
    tool = EchoTool()

    metadata = tool.metadata()

    assert metadata.id == "echo"
    assert metadata.permissions == frozenset()


def test_echo_tool_returns_request_unchanged() -> None:
    tool = EchoTool()
    context = _make_context()

    result = ToolExecutionPipeline().run(tool, context, {"message": "hi"})

    assert result.success is True
    assert result.payload == {"message": "hi"}
