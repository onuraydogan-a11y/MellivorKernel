"""LocalProvider integration through factory, registry, and AIEngine."""

from __future__ import annotations

import httpx

from mellivor_kernel.ai_engine import AIEngineBuilder
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers import ProviderConfiguration, ProviderFactory, ProviderRegistry
from mellivor_kernel.providers.local import LocalProvider


def _provider(text: str = "local result") -> LocalProvider:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "qwen-local",
                "choices": [
                    {"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LocalProvider(
        ProviderConfiguration(
            provider_name="local",
            default_model="qwen-local",
            base_url="http://inference.internal:8000/v1",
        ),
        client=client,
    )


def test_factory_and_registry_integration() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("local", LocalProvider)
    configuration = ProviderConfiguration(
        provider_name="local",
        default_model="qwen-local",
        base_url="http://inference.internal:8000/v1",
    )

    provider = factory.create(configuration)
    registry = ProviderRegistry()
    registry.register(provider)

    assert registry.get("local") is provider


def test_full_execution_path() -> None:
    registry = ProviderRegistry()
    registry.register(_provider("executed locally"))
    runtime = (
        BootstrapBuilder(load_config({"MELLIVOR_ENVIRONMENT": "test"}))
        .with_provider_registry(registry)
        .build()
    )
    engine = AIEngineBuilder(runtime).build()

    result = engine.execute(
        ExecutionRequest(
            target=ExecutionTarget.PROVIDER,
            operation="local",
            payload={"messages": [{"role": "user", "content": "Hello"}]},
        ),
        engine.execution_context(),
    )

    assert result.success is True
    assert result.payload is not None
    assert result.payload["text"] == "executed locally"
    assert result.metadata["target"] == "provider"
