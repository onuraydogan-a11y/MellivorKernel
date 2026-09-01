"""Tests for the internal experimental embedding foundation."""

from __future__ import annotations

import inspect
import json
import math
from collections.abc import Callable
from typing import cast

import httpx
import pytest

from mellivor_kernel.providers import ProviderConfiguration, ProviderConfigurationError
from mellivor_kernel.providers._embeddings import (
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
    OpenAICompatibleEmbeddingProvider,
)


def _config(**overrides: object) -> ProviderConfiguration:
    values: dict[str, object] = {
        "provider_name": "openai-compatible-embedding",
        "default_model": "embed-model",
        "base_url": "http://embedding.internal:8000/v1",
    }
    values.update(overrides)
    return ProviderConfiguration(**values)  # type: ignore[arg-type]


def _response(
    vectors: list[list[object]] | None = None,
    *,
    indices: list[object] | None = None,
    model: object = "embed-model",
) -> dict[str, object]:
    values = vectors if vectors is not None else [[1.0, 0.0], [0.0, 1.0]]
    positions = indices if indices is not None else list(range(len(values)))
    return {
        "model": model,
        "data": [
            {"index": index, "embedding": vector}
            for index, vector in zip(positions, values, strict=True)
        ],
    }


def _provider(
    handler: Callable[[httpx.Request], httpx.Response], **config: object
) -> OpenAICompatibleEmbeddingProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleEmbeddingProvider(_config(**config), client=client)


def _json(request: httpx.Request) -> dict[str, object]:
    payload = json.loads(request.content)
    assert isinstance(payload, dict)
    return payload


def test_request_requires_a_non_empty_tuple() -> None:
    with pytest.raises(EmbeddingError):
        EmbeddingRequest(texts=())
    with pytest.raises(EmbeddingError):
        EmbeddingRequest(texts=["text"])  # type: ignore[arg-type]


@pytest.mark.parametrize("text", ["", "   ", 1, None])
def test_request_rejects_non_string_or_blank_text(text: object) -> None:
    with pytest.raises(EmbeddingError):
        EmbeddingRequest(texts=(text,))  # type: ignore[arg-type]


def test_request_preserves_duplicates_and_order_and_redacts_repr() -> None:
    request = EmbeddingRequest(texts=("secret-b", "secret-a", "secret-b"))

    assert request.texts == ("secret-b", "secret-a", "secret-b")
    assert "secret" not in repr(request)


def test_result_normalizes_numeric_values_and_redacts_vectors() -> None:
    result = EmbeddingResult(
        vectors=((1, 2.5), (3.0, 4)),
        model="embed-model",
        dimensions=2,
    )

    assert result.vectors == ((1.0, 2.5), (3.0, 4.0))
    assert "1.0" not in repr(result)


@pytest.mark.parametrize(
    ("vectors", "model", "dimensions"),
    [
        ((), "model", 2),
        (((1.0,),), "", 1),
        (((1.0,),), "model", 0),
        (((1.0,),), "model", True),
        (((1.0,), (1.0, 2.0)), "model", 1),
        (((math.nan,),), "model", 1),
        (((math.inf,),), "model", 1),
        (((True,),), "model", 1),
        (((),), "model", 1),
    ],
)
def test_result_rejects_invalid_shape_and_values(
    vectors: object, model: object, dimensions: object
) -> None:
    with pytest.raises(EmbeddingError):
        EmbeddingResult(
            vectors=cast("tuple[tuple[float, ...], ...]", vectors),
            model=cast("str", model),
            dimensions=cast("int", dimensions),
        )


def test_adapter_conforms_to_protocol_and_not_base_provider() -> None:
    provider = _provider(lambda _request: httpx.Response(200, json=_response([[1.0]])))

    assert isinstance(provider, EmbeddingProvider)
    assert provider.name == "openai-compatible-embedding"


def test_construction_performs_no_network_call() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_response([[1.0]]))

    _provider(handler)

    assert calls == 0


@pytest.mark.parametrize("value", [None, "", "   "])
def test_adapter_requires_configured_model(value: object) -> None:
    with pytest.raises(ProviderConfigurationError):
        OpenAICompatibleEmbeddingProvider(_config(default_model=value))


@pytest.mark.parametrize("value", [None, ""])
def test_adapter_requires_endpoint(value: object) -> None:
    with pytest.raises(ProviderConfigurationError):
        OpenAICompatibleEmbeddingProvider(_config(base_url=value))


@pytest.mark.parametrize(
    "url",
    [
        "localhost:8000/v1",
        "ftp://host/v1",
        "http:///v1",
        "http://user:password@host/v1",
        "http://host/v1?token=secret",
        "http://host/v1#secret",
    ],
)
def test_adapter_rejects_unsafe_or_ambiguous_endpoint(url: str) -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        OpenAICompatibleEmbeddingProvider(_config(base_url=url))

    assert "password" not in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_success_maps_request_auth_endpoint_and_reorders_response() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=_response([[0.0, 1.0], [1.0, 0.0]], indices=[1, 0]),
        )

    result = _provider(handler, api_key="top-secret").embed(
        EmbeddingRequest(texts=("first-private-text", "second-private-text"))
    )

    assert result == EmbeddingResult(
        vectors=((1.0, 0.0), (0.0, 1.0)),
        model="embed-model",
        dimensions=2,
    )
    assert str(seen[0].url) == "http://embedding.internal:8000/v1/embeddings"
    assert seen[0].headers["Authorization"] == "Bearer top-secret"
    assert _json(seen[0]) == {
        "model": "embed-model",
        "input": ["first-private-text", "second-private-text"],
    }


def test_no_auth_header_when_key_absent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=_response([[1.0]]))

    _provider(handler).embed(EmbeddingRequest(texts=("text",)))


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"model": "embed-model", "data": []},
        {"model": "embed-model", "data": ["bad"]},
        _response([[1.0]], indices=[-1]),
        _response([[1.0]], indices=[1]),
        _response([[1.0], [2.0]], indices=[0, 0]),
        _response([[1.0], [2.0, 3.0]]),
        _response([[]]),
        _response([[True]]),
        _response([[1.0]], model="other-model"),
        _response([[1.0]], model=""),
    ],
)
def test_malformed_responses_translate_without_sensitive_data(payload: object) -> None:
    provider = _provider(lambda _request: httpx.Response(200, json=payload), api_key="top-secret")

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    message = str(exc_info.value)
    assert "private-input" not in message
    assert "top-secret" not in message


@pytest.mark.parametrize("non_finite", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_response_vectors_are_translated(non_finite: str) -> None:
    body = f'{{"model":"embed-model","data":[{{"index":0,"embedding":[{non_finite}]}}]}}'
    provider = _provider(
        lambda _request: httpx.Response(
            200, content=body, headers={"content-type": "application/json"}
        )
    )

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))
    message = str(exc_info.value)
    assert "private-input" not in message
    assert non_finite not in message
    assert "Authorization" not in message


def test_invalid_json_is_translated_without_raw_body() -> None:
    provider = _provider(lambda _request: httpx.Response(200, text="private raw body"))

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    assert "private" not in str(exc_info.value)


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_error_is_redacted(status: int) -> None:
    provider = _provider(
        lambda _request: httpx.Response(status, text="top-secret raw body"),
        api_key="top-secret",
    )

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    assert "top-secret" not in str(exc_info.value)
    assert "private-input" not in str(exc_info.value)


def test_http_error_is_translated_without_body() -> None:
    provider = _provider(lambda _request: httpx.Response(500, text="private diagnostics"))

    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    assert str(exc_info.value) == "Embedding endpoint request failed with HTTP 500."


def test_timeout_retries_and_translates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("top-secret timeout", request=request)

    provider = _provider(handler, max_retries=2, api_key="top-secret")
    with pytest.raises(EmbeddingError) as exc_info:
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    assert calls == 3
    assert "top-secret" not in str(exc_info.value)
    assert "private-input" not in str(exc_info.value)


def test_transport_error_retries_and_translates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("private transport", request=request)

    provider = _provider(handler, max_retries=1)
    with pytest.raises(EmbeddingError):
        provider.embed(EmbeddingRequest(texts=("private-input",)))

    assert calls == 2


def test_non_retryable_http_error_is_attempted_once() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    provider = _provider(handler, max_retries=3)
    with pytest.raises(EmbeddingError):
        provider.embed(EmbeddingRequest(texts=("text",)))

    assert calls == 1


def test_health_check_success_and_failure() -> None:
    healthy = _provider(lambda _request: httpx.Response(200, json=_response([[1.0]])))
    unhealthy = _provider(lambda _request: httpx.Response(503, text="private"))

    assert healthy.check_health().healthy is True
    report = unhealthy.check_health()
    assert report.healthy is False
    assert report.provider_name == "openai-compatible-embedding"
    assert "private" not in report.detail


def test_adapter_rejects_wrong_request_type_without_network() -> None:
    provider = _provider(lambda _request: pytest.fail("network must not be reached"))

    with pytest.raises(EmbeddingError):
        provider.embed(object())  # type: ignore[arg-type]


def test_modules_contain_no_process_or_runtime_management() -> None:
    module = __import__("mellivor_kernel.providers._embeddings.openai_compatible", fromlist=["*"])
    source = inspect.getsource(module)

    assert "subprocess" not in source
    assert "Popen" not in source
    assert "os.system" not in source
    assert "eval(" not in source
    assert "exec(" not in source
    assert "download" not in source
