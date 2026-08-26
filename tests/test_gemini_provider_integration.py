"""Integration tests: GeminiProvider registered and dispatched through the
full kernel stack -- via `AIEngine`, never a hand-built `Dispatcher`/
`ExecutionEngine`.

Proves the acceptance criterion for Sprint 29: `AIEngineBuilder ->
AIEngine.execute() -> ExecutionEngine -> Authorization -> Dispatcher ->
GeminiProvider -> ExecutionResult` works end-to-end with no architectural
change to `execution`, `authorization`, or `ai_engine` -- all three are
used completely unmodified here, exactly as they were for `OpenAIProvider`
in Sprint 23. Mirrors `test_openai_provider_integration.py`'s structure.

Never calls the live Gemini API -- a fake client is injected the same way
`tests/providers/test_gemini.py` does.

Skipped entirely if the optional `google-genai` package is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from google import genai
else:
    genai = pytest.importorskip("google.genai")

from google.genai import types

from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderFactory,
    ProviderRegistry,
)
from mellivor_kernel.providers.gemini import GeminiProvider


class _FakeModels:
    def __init__(self, response: types.GenerateContentResponse) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> types.GenerateContentResponse:
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: types.GenerateContentResponse) -> None:
        self.models = _FakeModels(response)


def _make_response(text: str = "Paris is the capital of France.") -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
        finish_reason=types.FinishReason.STOP,
    )
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=12, candidates_token_count=8, total_token_count=20
    )
    return types.GenerateContentResponse(candidates=[candidate], usage_metadata=usage)


def _make_provider(response_text: str = "Paris is the capital of France.") -> GeminiProvider:
    fake_client = _FakeClient(_make_response(response_text))
    configuration = ProviderConfiguration(
        provider_name="gemini", api_key="test-key", default_model="gemini-2.0-flash-001"
    )
    return GeminiProvider(configuration, client=cast(genai.Client, fake_client))


def test_provider_registration_via_factory_and_registry() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("gemini", GeminiProvider)
    registry = ProviderRegistry()

    configuration = ProviderConfiguration(
        provider_name="gemini", api_key="test-key", default_model="gemini-2.0-flash-001"
    )
    provider = factory.create(configuration)
    registry.register(provider)

    resolved = registry.get("gemini")
    assert resolved.name == "gemini"
    assert registry.is_registered("gemini") is True


def test_full_execution_flow_through_ai_engine() -> None:
    """`AIEngineBuilder(runtime).build().execute()` -- proving the new
    provider is reachable through the AI Engine Foundation, not around
    it, with no authorization configured.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    provider_registry = ProviderRegistry()
    provider_registry.register(_make_provider("The capital of France is Paris."))
    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    engine = AIEngineBuilder(runtime).build()
    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="gemini",
        payload={"messages": [{"role": "user", "content": "What is the capital of France?"}]},
    )

    result = engine.execute(request, engine.execution_context())

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "The capital of France is Paris."
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
        operation="gemini",
        payload={"messages": [{"role": "user", "content": "What is the capital of France?"}]},
    )

    result = engine.execute(request, engine.execution_context())

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "Paris is the capital of France."
