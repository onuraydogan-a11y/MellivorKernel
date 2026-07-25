"""End-to-end example: OpenAIProvider registered and invoked through the AI
Engine Foundation.

Demonstrates the kernel's second concrete provider, wired into the same
explicit `ProviderRegistry` composition `ClaudeProvider` already uses, and
invoked through `AIEngineBuilder`/`AIEngine.execute()` rather than a
hand-built `Dispatcher`/`ExecutionEngine` -- unlike
`execution_provider_invocation.py`, which predates the AI Engine
Foundation.

Uses a fake, injected OpenAI client -- exercising `OpenAIProvider`'s real
request-building, validation, and response-parsing code, but making no
live network call and requiring no API key, the same way
`execution_provider_invocation.py`'s `EchoProvider` runs without calling
any external model. Requires the optional `openai` package:
`pip install mellivor-kernel[openai]`.

Run directly: `python examples/openai_provider_invocation.py`
"""

from __future__ import annotations

from typing import cast

import openai
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers import ProviderConfiguration, ProviderRegistry
from mellivor_kernel.providers.openai import OpenAIProvider


class _FakeCompletions:
    """Test-only stand-in for `openai.OpenAI().chat.completions`. Not for production use."""

    def create(self, **kwargs: object) -> ChatCompletion:
        return ChatCompletion(
            id="chatcmpl_example",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="The capital of France is Paris.",
                    ),
                )
            ],
            created=0,
            model="gpt-4o",
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=12, completion_tokens=8, total_tokens=20),
        )


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    """A fake standing in for `openai.OpenAI` -- no network call, no API key needed."""

    def __init__(self) -> None:
        self.chat = _FakeChat()


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "WARNING"})

    provider_registry = ProviderRegistry()
    provider_registry.register(
        OpenAIProvider(
            ProviderConfiguration(
                provider_name="openai", api_key="sk-example", default_model="gpt-4o"
            ),
            client=cast(openai.OpenAI, _FakeClient()),
        )
    )

    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()
    engine = AIEngineBuilder(runtime).build()

    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="openai",
        payload={"messages": [{"role": "user", "content": "What is the capital of France?"}]},
    )

    result = engine.execute(request, engine.execution_context())

    print(f"success={result.success}")
    print(f"payload={result.payload}")
    print(f"execution_time_seconds={result.execution_time_seconds:.6f}")
    print(f"metadata={dict(result.metadata)}")

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "The capital of France is Paris."


if __name__ == "__main__":
    main()
