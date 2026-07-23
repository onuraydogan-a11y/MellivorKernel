"""Tests for mellivor_kernel.execution.engine."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_engine"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def _make_engine(*, register_echo: bool = True) -> ExecutionEngine:
    tool_registry = ToolRegistry()
    if register_echo:
        tool_registry.register(EchoTool())
    dispatcher = Dispatcher(tool_registry, ProviderRegistry())
    return ExecutionEngine(dispatcher)


def test_engine_executes_successful_tool_request() -> None:
    engine = _make_engine()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = engine.execute(request, _make_context())

    assert result.success is True
    assert result.payload == {"x": 1}


def test_engine_returns_failed_result_for_unregistered_operation() -> None:
    engine = _make_engine(register_echo=False)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.execute(request, _make_context())

    assert result.success is False
    assert result.error is not None


def test_engine_is_the_single_entry_point_regardless_of_target() -> None:
    engine = _make_engine()
    context = _make_context()

    tool_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo"), context
    )
    provider_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="missing"), context
    )

    assert tool_result.metadata["target"] == "tool"
    assert provider_result.metadata["target"] == "provider"
    assert provider_result.success is False
