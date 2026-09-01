"""Deterministic tests for the optional OpenAI-compatible LocalProvider."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable

import httpx
import pytest

from mellivor_kernel.providers import (
    BaseProvider,
    ProviderConfiguration,
    ProviderConfigurationError,
)
from mellivor_kernel.providers.local import (
    LocalAuthenticationError,
    LocalConnectionError,
    LocalProvider,
    LocalProviderError,
    LocalResponseError,
    LocalTimeoutError,
)


def _config(**overrides: object) -> ProviderConfiguration:
    values: dict[str, object] = {
        "provider_name": "local",
        "default_model": "qwen-local",
        "base_url": "http://inference.internal:8000/v1",
    }
    values.update(overrides)
    return ProviderConfiguration(**values)  # type: ignore[arg-type]


def _response(
    text: str = "local answer",
    *,
    model: str = "qwen-local",
    finish_reason: str | None = "stop",
    usage: object = None,
) -> dict[str, object]:
    return {
        "model": model,
        "choices": [
            {"message": {"role": "assistant", "content": text}, "finish_reason": finish_reason}
        ],
        "usage": usage if usage is not None else {"prompt_tokens": 7, "completion_tokens": 3},
    }


def _provider(
    handler: Callable[[httpx.Request], httpx.Response], **config: object
) -> LocalProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LocalProvider(_config(**config), client=client)


def _json(request: httpx.Request) -> dict[str, object]:
    payload = json.loads(request.content)
    assert isinstance(payload, dict)
    return payload


def test_is_base_provider_with_minimal_capabilities() -> None:
    provider = _provider(lambda _request: httpx.Response(200, json=_response()))

    assert isinstance(provider, BaseProvider)
    assert provider.name == "local"
    assert provider.capabilities.supports_streaming is False
    assert provider.capabilities.supports_tool_calls is False
    assert provider.capabilities.supports_vision is False
    assert provider.capabilities.supports_embeddings is False


def test_construction_performs_no_network_call() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_response())

    _provider(handler)

    assert calls == 0


@pytest.mark.parametrize("value", [None, "", "   "])
def test_requires_default_model(value: object) -> None:
    with pytest.raises(ProviderConfigurationError):
        LocalProvider(_config(default_model=value))


@pytest.mark.parametrize("value", [None, ""])
def test_requires_explicit_base_url(value: object) -> None:
    with pytest.raises(ProviderConfigurationError):
        LocalProvider(_config(base_url=value))


@pytest.mark.parametrize(
    "url",
    [
        "localhost:8000/v1",
        "ftp://host/v1",
        "http:///v1",
        "http://user:password@host/v1",
        "http://host/v1?token=secret",
        "http://host/v1#fragment",
    ],
)
def test_rejects_unsafe_or_ambiguous_endpoint_urls(url: str) -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        LocalProvider(_config(base_url=url))

    assert "password" not in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_success_maps_messages_model_endpoint_and_usage() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_response("hello"))

    provider = _provider(handler)
    result = provider.invoke(
        {
            "messages": [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
            "max_tokens": 55,
        }
    )

    assert result == {
        "text": "hello",
        "model": "qwen-local",
        "finish_reason": "stop",
        "prompt_tokens": 7,
        "completion_tokens": 3,
    }
    assert str(seen[0].url) == "http://inference.internal:8000/v1/chat/completions"
    assert _json(seen[0]) == {
        "model": "qwen-local",
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ],
        "max_tokens": 55,
        "stream": False,
    }


def test_default_max_tokens_and_missing_usage_normalize() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(_json(request))
        return httpx.Response(200, json=_response(usage={}))

    result = _provider(handler).invoke({"messages": [{"role": "user", "content": "Hello"}]})

    assert seen[0]["max_tokens"] == 1024
    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"messages": []},
        {"messages": ["bad"]},
        {"messages": [{"role": "tool", "content": "bad"}]},
        {"messages": [{"role": "user", "content": 1}]},
        {"messages": [{"role": "user", "content": "x"}], "max_tokens": True},
        {"messages": [{"role": "user", "content": "x"}], "max_tokens": 0},
        {"messages": [{"role": "user", "content": "x"}], "tools": []},
    ],
)
def test_rejects_malformed_or_unsupported_requests(payload: dict[str, object]) -> None:
    provider = _provider(lambda _request: pytest.fail("network must not be reached"))

    with pytest.raises(LocalProviderError):
        provider.invoke(payload)


def test_optional_bearer_authentication_header() -> None:
    headers: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        headers.append(request.headers.get("Authorization"))
        return httpx.Response(200, json=_response())

    _provider(handler, api_key="local-secret").invoke(
        {"messages": [{"role": "user", "content": "Hello"}]}
    )

    assert headers == ["Bearer local-secret"]


def test_no_authentication_header_when_key_is_absent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=_response())

    _provider(handler).invoke({"messages": [{"role": "user", "content": "Hello"}]})


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_failure_is_translated_without_secret(status: int) -> None:
    provider = _provider(
        lambda _request: httpx.Response(status, text="local-secret vendor body"),
        api_key="local-secret",
    )

    with pytest.raises(LocalAuthenticationError) as exc_info:
        provider.invoke({"messages": [{"role": "user", "content": "Hello"}]})

    assert "local-secret" not in str(exc_info.value)


def test_http_failure_excludes_response_body_and_secret() -> None:
    provider = _provider(
        lambda _request: httpx.Response(500, text="local-secret internal diagnostics"),
        api_key="local-secret",
    )

    with pytest.raises(LocalProviderError) as exc_info:
        provider.invoke({"messages": [{"role": "user", "content": "Hello"}]})

    assert str(exc_info.value) == "Local inference endpoint request failed with HTTP 500."


def test_timeout_is_retried_and_translated() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("vendor timeout local-secret", request=request)

    provider = _provider(handler, api_key="local-secret", max_retries=2)
    with pytest.raises(LocalTimeoutError) as exc_info:
        provider.invoke({"messages": [{"role": "user", "content": "Hello"}]})

    assert calls == 3
    assert "local-secret" not in str(exc_info.value)


def test_connection_failure_is_retried_and_translated() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("vendor connection details", request=request)

    provider = _provider(handler, max_retries=1)
    with pytest.raises(LocalConnectionError):
        provider.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    assert calls == 2


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
        httpx.Response(200, json=_response(usage={"prompt_tokens": -1})),
    ],
)
def test_malformed_responses_are_translated(response: httpx.Response) -> None:
    provider = _provider(lambda _request: response)

    with pytest.raises(LocalResponseError):
        provider.invoke({"messages": [{"role": "user", "content": "Hello"}]})


def test_health_check_success_and_failure() -> None:
    healthy = _provider(lambda _request: httpx.Response(200, json=_response()))
    unhealthy = _provider(lambda _request: httpx.Response(503, text="unavailable"))

    assert healthy.check_health().healthy is True
    report = unhealthy.check_health()
    assert report.healthy is False
    assert report.provider_name == "local"
    assert "503" in report.detail


def test_module_contains_no_process_or_runtime_management() -> None:
    source = inspect.getsource(__import__("mellivor_kernel.providers.local", fromlist=["*"]))

    assert "subprocess" not in source
    assert "Popen" not in source
    assert "os.system" not in source
    assert "eval(" not in source
    assert "exec(" not in source
