"""Integration Gate #1 (Sprint 7): end-to-end validation of Execution Core
against a bootstrapped runtime.

Mirrors `examples/execution_tool_invocation.py` and
`examples/execution_provider_invocation.py`, exercised as pytest assertions
rather than a printed script, plus the failure paths a real caller would
also need to handle.
"""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.core import KernelState
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
)


class _EchoProvider(BaseProvider):
    """Test-only provider satisfying `BaseProvider`. Not a production integration."""

    @property
    def name(self) -> str:
        return "echo-provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=False)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echoed": dict(request)}


def test_tool_invocation_path_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()
    assert runtime.state == KernelState.RUNNING

    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    request = ExecutionRequest(
        target=ExecutionTarget.TOOL, operation="echo", payload={"ping": "pong"}
    )

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert result.payload == {"ping": "pong"}
    assert result.metadata["target"] == "tool"
    assert result.execution_time_seconds >= 0.0


def test_provider_invocation_path_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_EchoProvider(ProviderConfiguration(provider_name="echo-provider")))
    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER, operation="echo-provider", payload={"prompt": "hi"}
    )

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert result.payload == {"echoed": {"prompt": "hi"}}
    assert result.metadata["target"] == "provider"


def test_engine_dispatches_both_paths_from_the_same_runtime() -> None:
    """A single ExecutionEngine, built from a single bootstrapped runtime,
    is the one entry point for both targets -- proving Execution Core
    doesn't need per-target wiring at the call site.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_EchoProvider(ProviderConfiguration(provider_name="echo-provider")))
    runtime = (
        BootstrapBuilder(config)
        .with_provider_registry(provider_registry)
        .with_builtin_tools()
        .build()
    )
    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    context = runtime.execution_context()

    tool_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="version"), context
    )
    provider_result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="echo-provider"), context
    )

    assert tool_result.success is True
    assert provider_result.success is True


def test_unregistered_tool_operation_fails_cleanly_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).build()
    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="does-not-exist"),
        runtime.execution_context(),
    )

    assert result.success is False
    assert result.error is not None


def test_unregistered_provider_operation_fails_cleanly_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).build()
    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="does-not-exist"),
        runtime.execution_context(),
    )

    assert result.success is False
    assert result.error is not None
