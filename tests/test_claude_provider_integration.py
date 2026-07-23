"""Integration tests: ClaudeProvider registered and dispatched through the
full kernel stack.

Proves the acceptance criterion for Sprint 10: `ExecutionRequest ->
ExecutionEngine -> Authorization -> Dispatcher -> ClaudeProvider ->
ExecutionResult` works end-to-end with no architectural change to
`execution` or `authorization` -- both are used completely unmodified
here, exactly as they were for the test-only `EchoProvider` in Sprint 7.

Never calls the live Anthropic API -- a fake client is injected the same
way `tests/providers/test_claude.py` does.

Skipped entirely if the optional `anthropic` package is not installed --
see `tests/providers/test_claude.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    # A real import, so `anthropic.Anthropic` resolves as a type below. At
    # runtime the `importorskip` call in the `else` branch is what actually
    # guards against `anthropic` not being installed.
    import anthropic
else:
    anthropic = pytest.importorskip("anthropic")

from anthropic.types import Message, TextBlock, Usage

from mellivor_kernel.authorization import AuthorizationEngine, PermissionResolver
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderFactory,
    ProviderRegistry,
)
from mellivor_kernel.providers.claude import ClaudeProvider
from mellivor_kernel.tools import ToolRegistry


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


class _FakeMessages:
    def __init__(self, response: Message) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Message:
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: Message) -> None:
        self.messages = _FakeMessages(response)


def _make_message(text: str = "The capital of France is Paris.") -> Message:
    return Message(
        id="msg_1",
        content=[TextBlock(text=text, type="text")],
        model="claude-sonnet-5",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=12, output_tokens=8),
    )


def _make_provider(response_text: str = "The capital of France is Paris.") -> ClaudeProvider:
    fake_client = _FakeClient(_make_message(response_text))
    configuration = ProviderConfiguration(
        provider_name="claude", api_key="sk-ant-test", default_model="claude-sonnet-5"
    )
    return ClaudeProvider(configuration, client=cast(anthropic.Anthropic, fake_client))


def _context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_claude_provider_integration"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_provider_registration_via_factory_and_registry() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("claude", ClaudeProvider)
    registry = ProviderRegistry()

    configuration = ProviderConfiguration(
        provider_name="claude", api_key="sk-ant-test", default_model="claude-sonnet-5"
    )
    provider = factory.create(configuration)
    registry.register(provider)

    resolved = registry.get("claude")
    assert resolved.name == "claude"
    assert registry.is_registered("claude") is True


def test_provider_dispatch_through_the_dispatcher() -> None:
    provider = _make_provider()
    provider_registry = ProviderRegistry()
    provider_registry.register(provider)

    dispatcher = Dispatcher(tool_registry=ToolRegistry(), provider_registry=provider_registry)
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER, operation="claude", payload={"prompt": "What is 2+2?"}
    )

    result = dispatcher.dispatch(request, _context())

    assert result.success is True
    assert result.payload == {
        "text": "The capital of France is Paris.",
        "model": "claude-sonnet-5",
        "stop_reason": "end_turn",
        "input_tokens": 12,
        "output_tokens": 8,
    }
    assert result.metadata["target"] == "provider"


def test_full_execution_flow_through_authorization_and_dispatch() -> None:
    """ExecutionRequest -> ExecutionEngine -> Authorization -> Dispatcher
    -> ClaudeProvider -> ExecutionResult, with authorization wired in
    (unmodified from Sprint 8) proving it imposes no requirement on --
    and needs no change for -- a provider target.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider = _make_provider("Paris is the capital of France.")
    provider_registry = ProviderRegistry()
    provider_registry.register(provider)

    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry))
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), authorizer=authorizer
    )
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="claude",
        payload={"prompt": "What is the capital of France?"},
    )

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "Paris is the capital of France."
