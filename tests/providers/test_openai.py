"""Tests for mellivor_kernel.providers.openai.

Never calls the live OpenAI API -- every test injects a fake client (or
constructs real `openai` SDK exception/response types directly, without
any network I/O) via `OpenAIProvider`'s `client` constructor parameter.

Skipped entirely if the optional `openai` package is not installed
(`pip install mellivor-kernel[openai]`) -- CI always installs it, but a
plain `pip install -e ".[dev]"` should still leave the rest of the suite
green.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    # Real imports, so `openai.OpenAI`/`httpx.Request`/`httpx.Response`
    # resolve as types below. At runtime the `importorskip` calls in the
    # `else` branch are what actually guard against `openai` (and its
    # `httpx` dependency) not being installed.
    import httpx
    import openai
else:
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderConfigurationError,
)
from mellivor_kernel.providers.openai import (
    OpenAIAuthenticationError,
    OpenAIConnectionError,
    OpenAIProvider,
    OpenAIProviderError,
    OpenAIResponseError,
    OpenAITimeoutError,
)


class _FakeCompletions:
    def __init__(
        self, *, response: ChatCompletion | None = None, error: Exception | None = None
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> ChatCompletion:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(
        self, *, response: ChatCompletion | None = None, error: Exception | None = None
    ) -> None:
        self.chat = _FakeChat(_FakeCompletions(response=response, error=error))

    @property
    def completions(self) -> _FakeCompletions:
        return self.chat.completions


def _as_client(fake: _FakeClient) -> openai.OpenAI:
    return cast(openai.OpenAI, fake)


def _make_completion(text: str = "hello world") -> ChatCompletion:
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
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _config(**overrides: object) -> ProviderConfiguration:
    defaults: dict[str, object] = {
        "provider_name": "openai",
        "api_key": "sk-test",
        "default_model": "gpt-4o",
    }
    defaults.update(overrides)
    return ProviderConfiguration(**defaults)  # type: ignore[arg-type]


def _http_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _http_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_http_request())


# -- construction / configuration ---------------------------------------------


def test_construction_requires_api_key() -> None:
    with pytest.raises(ProviderConfigurationError):
        OpenAIProvider(_config(api_key=None))


def test_construction_requires_default_model() -> None:
    with pytest.raises(ProviderConfigurationError):
        OpenAIProvider(_config(default_model=None))


def test_name_and_capabilities() -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    assert provider.name == "openai"
    assert provider.capabilities.supports_streaming is False
    assert provider.capabilities.supports_tool_calls is False


# -- successful completion -----------------------------------------------------


def test_successful_completion_returns_text_and_metadata() -> None:
    fake = _FakeClient(response=_make_completion("hi there"))
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    result = provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert result == {
        "text": "hi there",
        "model": "gpt-4o",
        "finish_reason": "stop",
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }
    assert fake.completions.calls[0]["model"] == "gpt-4o"
    assert fake.completions.calls[0]["messages"] == [{"role": "user", "content": "hello"}]


def test_successful_completion_forwards_a_system_message() -> None:
    """OpenAI expresses a system prompt as an ordinary message with
    `role: "system"`, unlike ClaudeProvider's separate `system` field --
    the one deliberate structural difference this sprint surfaces.
    """
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    provider.invoke(
        {
            "messages": [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hello"},
            ]
        }
    )

    assert fake.completions.calls[0]["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hello"},
    ]


def test_successful_completion_uses_default_max_tokens_when_not_given() -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert fake.completions.calls[0]["max_tokens"] == 1024


def test_successful_completion_honors_explicit_max_tokens() -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}], "max_tokens": 50})

    assert fake.completions.calls[0]["max_tokens"] == 50


# -- request validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "request_payload",
    [
        {},
        {"messages": []},
        {"messages": "not-a-list"},
        {"messages": [5]},
        {"messages": [{"content": "hello"}]},
        {"messages": [{"role": ""}]},
        {"messages": [{"role": "user", "content": 5}]},
    ],
)
def test_invalid_messages_rejected(request_payload: Mapping[str, object]) -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIProviderError):
        provider.invoke(request_payload)


@pytest.mark.parametrize("max_tokens", [0, -1, "many", True])
def test_invalid_max_tokens_rejected(max_tokens: Any) -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIProviderError):
        provider.invoke(
            {"messages": [{"role": "user", "content": "hello"}], "max_tokens": max_tokens}
        )


# -- authentication failure -----------------------------------------------------


def test_authentication_failure_is_translated() -> None:
    error = openai.AuthenticationError("invalid api key", response=_http_response(401), body=None)
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIAuthenticationError) as excinfo:
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert "invalid api key" in str(excinfo.value)


# -- timeout --------------------------------------------------------------------


def test_timeout_is_translated() -> None:
    error = openai.APITimeoutError(request=_http_request())
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAITimeoutError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


# -- network failure --------------------------------------------------------------


def test_network_failure_is_translated() -> None:
    error = openai.APIConnectionError(message="Connection error.", request=_http_request())
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIConnectionError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_other_api_errors_fall_back_to_the_generic_provider_error() -> None:
    error = openai.RateLimitError("rate limited", response=_http_response(429), body=None)
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIProviderError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_sdk_exceptions_never_escape_the_provider() -> None:
    error = openai.AuthenticationError("invalid api key", response=_http_response(401), body=None)
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIProviderError):
        try:
            provider.invoke({"messages": [{"role": "user", "content": "hello"}]})
        except openai.OpenAIError:
            pytest.fail("an openai SDK exception leaked out of OpenAIProvider")


# -- malformed response -----------------------------------------------------------


def test_response_with_no_text_content_is_translated() -> None:
    empty_completion = ChatCompletion(
        id="chatcmpl_2",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content=None),
            )
        ],
        created=0,
        model="gpt-4o",
        object="chat.completion",
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=0, total_tokens=1),
    )
    fake = _FakeClient(response=empty_completion)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    with pytest.raises(OpenAIResponseError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


# -- check_health ---------------------------------------------------------------


def test_check_health_reports_healthy_on_success() -> None:
    fake = _FakeClient(response=_make_completion())
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is True
    assert report.provider_name == "openai"


def test_check_health_reports_unhealthy_on_failure() -> None:
    error = openai.AuthenticationError("invalid api key", response=_http_response(401), body=None)
    fake = _FakeClient(error=error)
    provider = OpenAIProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is False
    assert report.provider_name == "openai"
    assert "invalid api key" in report.detail
