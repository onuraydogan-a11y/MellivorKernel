"""Tests for mellivor_kernel.providers.claude.

Never calls the live Anthropic API -- every test injects a fake client (or
constructs real `anthropic` SDK exception/response types directly, without
any network I/O) via `ClaudeProvider`'s `client` constructor parameter.

Skipped entirely if the optional `anthropic` package is not installed
(`pip install mellivor-kernel[anthropic]`) -- CI always installs it, but a
plain `pip install -e ".[dev]"` should still leave the rest of the suite
green.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    # Real imports, so `anthropic.Anthropic`/`httpx.Request`/`httpx.Response`
    # resolve as types below. At runtime the `importorskip` calls in the
    # `else` branch are what actually guard against `anthropic` (and its
    # `httpx` dependency) not being installed.
    import anthropic
    import httpx
else:
    anthropic = pytest.importorskip("anthropic")
    httpx = pytest.importorskip("httpx")

from anthropic.types import Message, TextBlock, Usage

from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderConfigurationError,
)
from mellivor_kernel.providers.claude import (
    ClaudeAuthenticationError,
    ClaudeConnectionError,
    ClaudeProvider,
    ClaudeProviderError,
    ClaudeResponseError,
    ClaudeTimeoutError,
)


class _FakeMessages:
    def __init__(self, *, response: Message | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Message:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _FakeClient:
    def __init__(self, *, response: Message | None = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(response=response, error=error)


def _as_client(fake: _FakeClient) -> anthropic.Anthropic:
    return cast(anthropic.Anthropic, fake)


def _make_message(text: str = "hello world") -> Message:
    return Message(
        id="msg_1",
        content=[TextBlock(text=text, type="text")],
        model="claude-sonnet-5",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=10, output_tokens=5),
    )


def _config(**overrides: object) -> ProviderConfiguration:
    defaults: dict[str, object] = {
        "provider_name": "claude",
        "api_key": "sk-ant-test",
        "default_model": "claude-sonnet-5",
    }
    defaults.update(overrides)
    return ProviderConfiguration(**defaults)  # type: ignore[arg-type]


def _http_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _http_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_http_request())


# -- construction / configuration ---------------------------------------------


def test_construction_requires_api_key() -> None:
    with pytest.raises(ProviderConfigurationError):
        ClaudeProvider(_config(api_key=None))


def test_construction_requires_default_model() -> None:
    with pytest.raises(ProviderConfigurationError):
        ClaudeProvider(_config(default_model=None))


def test_name_and_capabilities() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    assert provider.name == "claude"
    assert provider.capabilities.supports_streaming is False
    assert provider.capabilities.supports_tool_calls is False


# -- successful completion -----------------------------------------------------


def test_successful_completion_returns_text_and_metadata() -> None:
    fake = _FakeClient(response=_make_message("hi there"))
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    result = provider.invoke({"prompt": "hello"})

    assert result == {
        "text": "hi there",
        "model": "claude-sonnet-5",
        "stop_reason": "end_turn",
        "input_tokens": 10,
        "output_tokens": 5,
    }
    assert fake.messages.calls[0]["model"] == "claude-sonnet-5"
    assert fake.messages.calls[0]["messages"] == [{"role": "user", "content": "hello"}]


def test_successful_completion_forwards_system_prompt() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    provider.invoke({"prompt": "hello", "system": "be terse"})

    assert fake.messages.calls[0]["system"] == "be terse"


def test_successful_completion_uses_default_max_tokens_when_not_given() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    provider.invoke({"prompt": "hello"})

    assert fake.messages.calls[0]["max_tokens"] == 1024


def test_successful_completion_honors_explicit_max_tokens() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    provider.invoke({"prompt": "hello", "max_tokens": 50})

    assert fake.messages.calls[0]["max_tokens"] == 50


# -- request validation ---------------------------------------------------------


@pytest.mark.parametrize("request_payload", [{}, {"prompt": ""}, {"prompt": "   "}, {"prompt": 5}])
def test_invalid_prompt_rejected(request_payload: Mapping[str, object]) -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeProviderError):
        provider.invoke(request_payload)


def test_invalid_system_rejected() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeProviderError):
        provider.invoke({"prompt": "hello", "system": 5})


@pytest.mark.parametrize("max_tokens", [0, -1, "many", True])
def test_invalid_max_tokens_rejected(max_tokens: Any) -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeProviderError):
        provider.invoke({"prompt": "hello", "max_tokens": max_tokens})


# -- authentication failure -----------------------------------------------------


def test_authentication_failure_is_translated() -> None:
    error = anthropic.AuthenticationError(
        "invalid x-api-key", response=_http_response(401), body=None
    )
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeAuthenticationError) as excinfo:
        provider.invoke({"prompt": "hello"})

    assert "invalid x-api-key" in str(excinfo.value)


# -- timeout --------------------------------------------------------------------


def test_timeout_is_translated() -> None:
    error = anthropic.APITimeoutError(request=_http_request())
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeTimeoutError):
        provider.invoke({"prompt": "hello"})


# -- network failure --------------------------------------------------------------


def test_network_failure_is_translated() -> None:
    error = anthropic.APIConnectionError(message="Connection error.", request=_http_request())
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeConnectionError):
        provider.invoke({"prompt": "hello"})


def test_other_api_errors_fall_back_to_the_generic_provider_error() -> None:
    error = anthropic.RateLimitError("rate limited", response=_http_response(429), body=None)
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeProviderError):
        provider.invoke({"prompt": "hello"})


def test_sdk_exceptions_never_escape_the_provider() -> None:
    error = anthropic.AuthenticationError(
        "invalid x-api-key", response=_http_response(401), body=None
    )
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeProviderError):
        try:
            provider.invoke({"prompt": "hello"})
        except anthropic.AnthropicError:
            pytest.fail("an anthropic SDK exception leaked out of ClaudeProvider")


# -- malformed response -----------------------------------------------------------


def test_response_with_no_text_content_is_translated() -> None:
    empty_message = Message(
        id="msg_2",
        content=[],
        model="claude-sonnet-5",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=1, output_tokens=0),
    )
    fake = _FakeClient(response=empty_message)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    with pytest.raises(ClaudeResponseError):
        provider.invoke({"prompt": "hello"})


# -- check_health ---------------------------------------------------------------


def test_check_health_reports_healthy_on_success() -> None:
    fake = _FakeClient(response=_make_message())
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is True
    assert report.provider_name == "claude"


def test_check_health_reports_unhealthy_on_failure() -> None:
    error = anthropic.AuthenticationError(
        "invalid x-api-key", response=_http_response(401), body=None
    )
    fake = _FakeClient(error=error)
    provider = ClaudeProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is False
    assert report.provider_name == "claude"
    assert "invalid x-api-key" in report.detail
