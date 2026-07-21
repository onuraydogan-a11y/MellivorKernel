"""Tests for mellivor_kernel.tools.base."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.tools import NETWORK_READ, BaseTool, ToolContext, ToolResult
from mellivor_kernel.tools.permissions import Permission


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


class _MinimalTool(BaseTool):
    @property
    def id(self) -> str:
        return "minimal"

    @property
    def name(self) -> str:
        return "Minimal Tool"

    @property
    def version(self) -> str:
        return "0.0.1"

    @property
    def description(self) -> str:
        return "A minimal tool for testing BaseTool."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"test"})

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset({NETWORK_READ})

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        return ToolResult(success=True, payload=dict(request))


def _make_context() -> ToolContext:
    settings = _FakeSettings()
    return ToolContext(
        configuration=settings,
        logger=get_logger("test_base"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_base_tool_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseTool()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated() -> None:
    class _Incomplete(BaseTool):
        @property
        def id(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]


def test_metadata_reflects_declared_properties() -> None:
    tool = _MinimalTool()

    metadata = tool.metadata()

    assert metadata.id == "minimal"
    assert metadata.name == "Minimal Tool"
    assert metadata.version == "0.0.1"
    assert metadata.description == "A minimal tool for testing BaseTool."
    assert metadata.capabilities == frozenset({"test"})
    assert metadata.permissions == frozenset({NETWORK_READ})


def test_execute_runs_directly() -> None:
    tool = _MinimalTool()
    context = _make_context()

    result = tool.execute(context, {"x": 1})

    assert result.success is True
    assert result.payload == {"x": 1}
