"""Tests for mellivor_kernel.execution.dispatch."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    DispatchError,
    ExecutionContext,
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
from mellivor_kernel.tools import BaseTool, ToolContext, ToolRegistry, ToolResult
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL, Permission


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_dispatch"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


class _EchoTool(BaseTool):
    def __init__(
        self,
        *,
        raises: Exception | None = None,
        required_permissions: frozenset[Permission] = frozenset(),
    ) -> None:
        self._raises = raises
        self._required_permissions = required_permissions

    @property
    def id(self) -> str:
        return "echo"

    @property
    def name(self) -> str:
        return "Echo"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Echoes its request back."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return self._required_permissions

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        if self._raises is not None:
            raise self._raises
        return ToolResult(success=True, payload=dict(request))


class _FakeProvider(BaseProvider):
    def __init__(self, configuration: ProviderConfiguration, *, raises: Exception | None = None):
        super().__init__(configuration)
        self._raises = raises

    @property
    def name(self) -> str:
        return "fake"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        if self._raises is not None:
            raise self._raises
        return {"echo": dict(request)}


def _make_dispatcher(
    *, tool: BaseTool | None = None, provider: BaseProvider | None = None
) -> Dispatcher:
    tool_registry = ToolRegistry()
    if tool is not None:
        tool_registry.register(tool)

    provider_registry = ProviderRegistry()
    if provider is not None:
        provider_registry.register(provider)

    return Dispatcher(tool_registry, provider_registry)


def test_dispatch_selects_tool_target_on_success() -> None:
    dispatcher = _make_dispatcher(tool=_EchoTool())
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is True
    assert result.payload == {"x": 1}
    assert result.metadata["target"] == "tool"


def test_dispatch_selects_provider_target_on_success() -> None:
    provider = _FakeProvider(ProviderConfiguration(provider_name="fake"))
    dispatcher = _make_dispatcher(provider=provider)
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER, operation="fake", payload={"prompt": "hi"}
    )

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is True
    assert result.payload == {"echo": {"prompt": "hi"}}
    assert result.metadata["target"] == "provider"
    assert result.execution_time_seconds >= 0.0


def test_dispatch_to_unregistered_tool_fails_without_raising() -> None:
    dispatcher = _make_dispatcher()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="missing")

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is False
    assert result.metadata["target"] == "tool"
    assert "missing" in (result.error or "")


def test_dispatch_to_unregistered_provider_fails_without_raising() -> None:
    dispatcher = _make_dispatcher()
    request = ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="missing")

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is False
    assert result.metadata["target"] == "provider"
    assert "missing" in (result.error or "")


def test_dispatch_translates_tool_execution_exception() -> None:
    dispatcher = _make_dispatcher(tool=_EchoTool(raises=RuntimeError("tool boom")))
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is False
    assert "tool boom" in (result.error or "")


def test_dispatch_translates_provider_invoke_exception() -> None:
    provider = _FakeProvider(
        ProviderConfiguration(provider_name="fake"), raises=RuntimeError("provider boom")
    )
    dispatcher = _make_dispatcher(provider=provider)
    request = ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="fake")

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is False
    assert "provider boom" in (result.error or "")


def test_dispatch_raises_for_unknown_target() -> None:
    dispatcher = _make_dispatcher()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")
    # `target` carries no dataclass-level validation of enum membership (only
    # `operation`/`request_id` are checked in `__post_init__`), so a caller
    # bypassing the type checker can still reach the dispatcher with an
    # unrecognized target -- exactly the case this test exercises.
    bogus_request = dataclasses.replace(request, target="workflow")  # type: ignore[arg-type]

    with pytest.raises(DispatchError):
        dispatcher.dispatch(bogus_request, _make_context())


def test_dispatch_denies_a_permissioned_tool_with_no_granted_permissions() -> None:
    dispatcher = _make_dispatcher(tool=_EchoTool(required_permissions=frozenset({KERNEL_INTERNAL})))
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = dispatcher.dispatch(request, _make_context())

    assert result.success is False
    assert result.metadata["stage"] == "permission_check"


def test_dispatch_forwards_granted_permissions_to_a_permissioned_tool() -> None:
    dispatcher = _make_dispatcher(tool=_EchoTool(required_permissions=frozenset({KERNEL_INTERNAL})))
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = dispatcher.dispatch(
        request, _make_context(), granted_permissions=frozenset({"kernel.internal"})
    )

    assert result.success is True
    assert result.payload == {"x": 1}


def test_dispatch_denies_cleanly_on_malformed_granted_permission_string() -> None:
    dispatcher = _make_dispatcher(tool=_EchoTool())
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = dispatcher.dispatch(
        request, _make_context(), granted_permissions=frozenset({"NOT VALID"})
    )

    assert result.success is False
    assert result.metadata["stage"] == "permission_check"


def test_dispatch_ignores_granted_permissions_for_provider_target() -> None:
    provider = _FakeProvider(ProviderConfiguration(provider_name="fake"))
    dispatcher = _make_dispatcher(provider=provider)
    request = ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="fake")

    result = dispatcher.dispatch(
        request, _make_context(), granted_permissions=frozenset({"anything.at.all"})
    )

    assert result.success is True
