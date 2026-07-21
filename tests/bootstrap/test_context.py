"""Tests for mellivor_kernel.bootstrap.context."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.bootstrap import RuntimeContext
from mellivor_kernel.core import Kernel, KernelState, ServiceContainer
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolContext, ToolExecutionPipeline, ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context(*, started: bool = True) -> RuntimeContext:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    if started:
        kernel.start()
    return RuntimeContext(
        kernel=kernel,
        configuration=settings,
        provider_registry=ProviderRegistry(),
        tool_registry=ToolRegistry(),
    )


def test_runtime_context_reflects_kernel_state() -> None:
    context = _make_context(started=True)

    assert context.state == KernelState.RUNNING
    assert context.health().healthy is True


def test_runtime_context_reports_not_started_kernel() -> None:
    context = _make_context(started=False)

    assert context.state == KernelState.NOT_STARTED
    assert context.health().healthy is False


def test_runtime_context_exposes_the_kernels_own_container() -> None:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    context = RuntimeContext(
        kernel=kernel,
        configuration=settings,
        provider_registry=ProviderRegistry(),
        tool_registry=ToolRegistry(),
    )

    assert context.services is kernel.container
    assert isinstance(context.services, ServiceContainer)


def test_runtime_context_exposes_configuration() -> None:
    settings = _FakeSettings(log_level="DEBUG")
    context = RuntimeContext(
        kernel=Kernel(settings),
        configuration=settings,
        provider_registry=ProviderRegistry(),
        tool_registry=ToolRegistry(),
    )

    assert context.configuration is settings


def test_runtime_context_exposes_the_given_registries() -> None:
    provider_registry = ProviderRegistry()
    tool_registry = ToolRegistry()
    settings = _FakeSettings()
    context = RuntimeContext(
        kernel=Kernel(settings),
        configuration=settings,
        provider_registry=provider_registry,
        tool_registry=tool_registry,
    )

    assert context.provider_registry is provider_registry
    assert context.tool_registry is tool_registry


def test_runtime_context_does_not_expose_lifecycle_control_or_the_kernel() -> None:
    context = _make_context()

    assert not hasattr(context, "start")
    assert not hasattr(context, "shutdown")
    assert not hasattr(context, "kernel")


def test_tool_context_wraps_this_runtimes_kernel_and_services() -> None:
    context = _make_context(started=True)

    tool_context = context.tool_context()

    assert isinstance(tool_context, ToolContext)
    assert tool_context.configuration is context.configuration
    assert tool_context.services is context.services
    assert tool_context.runtime.state == context.state


def test_tool_context_can_actually_run_a_tool() -> None:
    context = _make_context(started=True)

    result = ToolExecutionPipeline().run(EchoTool(), context.tool_context(), {"ping": "pong"})

    assert result.success is True
    assert result.payload == {"ping": "pong"}
