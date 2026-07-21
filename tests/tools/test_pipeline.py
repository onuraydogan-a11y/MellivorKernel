"""Tests for mellivor_kernel.tools.pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.tools import (
    NETWORK_READ,
    BaseTool,
    ToolContext,
    ToolExecutionPipeline,
    ToolResult,
    ToolValidationError,
)
from mellivor_kernel.tools.permissions import Permission


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context() -> ToolContext:
    settings = _FakeSettings()
    return ToolContext(
        configuration=settings,
        logger=get_logger("test_pipeline"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


class _AlwaysValidTool(BaseTool):
    def __init__(
        self,
        *,
        permissions: frozenset[Permission] = frozenset(),
        raises: Exception | None = None,
    ) -> None:
        self._permissions = permissions
        self._raises = raises

    @property
    def id(self) -> str:
        return "always-valid"

    @property
    def name(self) -> str:
        return "Always Valid Tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A tool that always passes validate()."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return self._permissions

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        if self._raises is not None:
            raise self._raises
        return ToolResult(success=True, payload=dict(request))


class _RejectingTool(_AlwaysValidTool):
    def validate(self, request: Mapping[str, object]) -> None:
        raise ToolValidationError("request rejected")


def test_successful_run() -> None:
    pipeline = ToolExecutionPipeline()
    context = _make_context()

    result = pipeline.run(_AlwaysValidTool(), context, {"x": 1})

    assert result.success is True
    assert result.payload == {"x": 1}
    assert result.execution_time_seconds >= 0.0


def test_validation_failure_short_circuits() -> None:
    pipeline = ToolExecutionPipeline()
    context = _make_context()

    result = pipeline.run(_RejectingTool(), context, {})

    assert result.success is False
    assert result.metadata["stage"] == "validate"
    assert result.execution_time_seconds == 0.0


def test_permission_denial_short_circuits_before_execute() -> None:
    pipeline = ToolExecutionPipeline()
    context = _make_context()
    tool = _AlwaysValidTool(permissions=frozenset({NETWORK_READ}))

    result = pipeline.run(tool, context, {}, granted_permissions=frozenset())

    assert result.success is False
    assert result.metadata["stage"] == "permission_check"
    denied = result.metadata["missing_permissions"]
    assert isinstance(denied, tuple)
    assert "network.read" in denied
    assert result.execution_time_seconds == 0.0


def test_execution_proceeds_when_permissions_granted() -> None:
    pipeline = ToolExecutionPipeline()
    context = _make_context()
    tool = _AlwaysValidTool(permissions=frozenset({NETWORK_READ}))

    result = pipeline.run(tool, context, {}, granted_permissions=frozenset({NETWORK_READ}))

    assert result.success is True


def test_unexpected_exception_is_translated_into_a_failed_result() -> None:
    pipeline = ToolExecutionPipeline()
    context = _make_context()
    tool = _AlwaysValidTool(raises=RuntimeError("boom"))

    result = pipeline.run(tool, context, {})

    assert result.success is False
    assert result.metadata["stage"] == "execute"
    assert "boom" in (result.error or "")


def test_pipeline_overrides_tool_reported_execution_time() -> None:
    class _LyingTool(_AlwaysValidTool):
        def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
            return ToolResult(success=True, execution_time_seconds=999.0)

    pipeline = ToolExecutionPipeline()
    context = _make_context()

    result = pipeline.run(_LyingTool(), context, {})

    assert result.execution_time_seconds < 999.0
