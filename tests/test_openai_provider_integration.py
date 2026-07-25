"""Integration tests: OpenAIProvider registered and dispatched through the
full kernel stack -- via `AIEngine`, never a hand-built `Dispatcher`/
`ExecutionEngine`.

Proves the acceptance criterion for Sprint 23: `AIEngineBuilder ->
AIEngine.execute() -> ExecutionEngine -> Authorization -> Dispatcher ->
OpenAIProvider -> ExecutionResult` works end-to-end with no architectural
change to `execution`, `authorization`, or `ai_engine` -- all three are
used completely unmodified here, exactly as `execution`/`authorization`
were for `ClaudeProvider` in Sprint 10. Unlike Sprint 10's own
integration test (which predates `ai_engine`), this sprint routes every
full-stack scenario through `AIEngine` rather than constructing
`Dispatcher`/`ExecutionEngine` by hand.

Never calls the live OpenAI API -- a fake client is injected the same
way `tests/providers/test_openai.py` does.

Skipped entirely if the optional `openai` package is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    import openai
else:
    openai = pytest.importorskip("openai")

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderFactory,
    ProviderRegistry,
)
from mellivor_kernel.providers.openai import OpenAIProvider


class _FakeCompletions:
    def __init__(self, response: ChatCompletion) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> ChatCompletion:
        self.calls.append(kwargs)
        return self._response


class _FakeChat:
    def __init__(self, response: ChatCompletion) -> None:
        self.completions = _FakeCompletions(response)


class _FakeClient:
    def __init__(self, response: ChatCompletion) -> None:
        self.chat = _FakeChat(response)


def _make_completion(text: str = "The capital of France is Paris.") -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl_1",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content=text),
            )
        ],
        created=0,
        model="gpt-4o",
        object="chat.completion",
        usage=CompletionUsage(prompt_tokens=12, completion_tokens=8, total_tokens=20),
    )


def _make_provider(response_text: str = "The capital of France is Paris.") -> OpenAIProvider:
    fake_client = _FakeClient(_make_completion(response_text))
    configuration = ProviderConfiguration(
        provider_name="openai", api_key="sk-test", default_model="gpt-4o"
    )
    return OpenAIProvider(configuration, client=cast(openai.OpenAI, fake_client))


def test_provider_registration_via_factory_and_registry() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("openai", OpenAIProvider)
    registry = ProviderRegistry()

    configuration = ProviderConfiguration(
        provider_name="openai", api_key="sk-test", default_model="gpt-4o"
    )
    provider = factory.create(configuration)
    registry.register(provider)

    resolved = registry.get("openai")
    assert resolved.name == "openai"
    assert registry.is_registered("openai") is True


def test_full_execution_flow_through_ai_engine() -> None:
    """`AIEngineBuilder(runtime).build().execute()` -- proving the new
    provider is reachable through the AI Engine Foundation, not around
    it, with no authorization configured.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_make_provider("Paris is the capital of France."))
    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    engine = AIEngineBuilder(runtime).build()
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="openai",
        payload={"messages": [{"role": "user", "content": "What is the capital of France?"}]},
    )

    result = engine.execute(request, engine.execution_context())

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "Paris is the capital of France."
    assert result.metadata["target"] == "provider"


def test_full_execution_flow_through_ai_engine_with_authorization() -> None:
    """The same flow with `.with_authorization()` wired in (unmodified
    from Sprint 8/22) proving it imposes no requirement on -- and needs
    no change for -- a provider target reached through `AIEngine`.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_make_provider())
    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    engine = AIEngineBuilder(runtime).with_authorization().build()
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="openai",
        payload={"messages": [{"role": "user", "content": "What is the capital of France?"}]},
    )

    result = engine.execute(request, engine.execution_context())

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "The capital of France is Paris."
