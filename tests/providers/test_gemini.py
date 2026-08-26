"""Tests for mellivor_kernel.providers.gemini.

Never calls the live Gemini API -- every test injects a fake client (or
constructs real `google.genai` SDK exception/response types directly,
without any network I/O) via `GeminiProvider`'s `client` constructor
parameter.

Skipped entirely if the optional `google-genai` package is not installed
(`pip install mellivor-kernel[gemini]`) -- CI always installs it, but a
plain `pip install -e ".[dev]"` should still leave the rest of the suite
green.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    # Real imports, so `genai.Client`/`httpx.TimeoutException` resolve as
    # types below. At runtime the `importorskip` calls in the `else`
    # branch are what actually guard against `google-genai` (and its
    # `httpx` dependency) not being installed.
    import httpx
    from google import genai
else:
    genai = pytest.importorskip("google.genai")
    httpx = pytest.importorskip("httpx")

from google.genai import errors, types

from mellivor_kernel.providers import (
    ProviderConfiguration,
    ProviderConfigurationError,
)
from mellivor_kernel.providers.gemini import (
    GeminiAuthenticationError,
    GeminiConnectionError,
    GeminiProvider,
    GeminiProviderError,
    GeminiResponseError,
    GeminiTimeoutError,
)


class _FakeModels:
    def __init__(
        self,
        *,
        response: types.GenerateContentResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> types.GenerateContentResponse:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _FakeClient:
    def __init__(
        self,
        *,
        response: types.GenerateContentResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.models = _FakeModels(response=response, error=error)


def _as_client(fake: _FakeClient) -> genai.Client:
    return cast(genai.Client, fake)


def _make_response(
    text: str = "hello world",
    *,
    finish_reason: types.FinishReason | None = types.FinishReason.STOP,
) -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
        finish_reason=finish_reason,
    )
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=10, candidates_token_count=5, total_token_count=15
    )
    return types.GenerateContentResponse(candidates=[candidate], usage_metadata=usage)


def _make_blocked_response(
    block_reason: types.BlockedReason = types.BlockedReason.SAFETY,
) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[],
        prompt_feedback=types.GenerateContentResponsePromptFeedback(block_reason=block_reason),
    )


def _config(**overrides: object) -> ProviderConfiguration:
    defaults: dict[str, object] = {
        "provider_name": "gemini",
        "api_key": "test-key",
        "default_model": "gemini-2.0-flash-001",
    }
    defaults.update(overrides)
    return ProviderConfiguration(**defaults)  # type: ignore[arg-type]


def _api_error(code: int, message: str) -> errors.APIError:
    return errors.ClientError(code, {"error": {"message": message, "status": "ERROR"}})


# -- construction / configuration ---------------------------------------------


def test_construction_requires_api_key() -> None:
    with pytest.raises(ProviderConfigurationError):
        GeminiProvider(_config(api_key=None))


def test_construction_requires_default_model() -> None:
    with pytest.raises(ProviderConfigurationError):
        GeminiProvider(_config(default_model=None))


def test_name_and_capabilities() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    assert provider.name == "gemini"
    assert provider.capabilities.supports_streaming is False
    assert provider.capabilities.supports_tool_calls is False


# -- successful completion -----------------------------------------------------


def test_successful_completion_returns_text_and_metadata() -> None:
    fake = _FakeClient(response=_make_response("hi there"))
    provider = GeminiProvider(_config(), client=_as_client(fake))

    result = provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert result == {
        "text": "hi there",
        "model": "gemini-2.0-flash-001",
        "finish_reason": "STOP",
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }
    assert fake.models.calls[0]["model"] == "gemini-2.0-flash-001"


def test_user_message_maps_to_gemini_user_role() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    contents = fake.models.calls[0]["contents"]
    assert isinstance(contents, list)
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "hello"


def test_assistant_message_maps_to_gemini_model_role() -> None:
    """Gemini's own vocabulary for a model turn is "model", not
    "assistant" -- the one true role-name translation this provider
    performs; see ADR-0023.
    """
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke(
        {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello back"},
                {"role": "user", "content": "and again"},
            ]
        }
    )

    contents = fake.models.calls[0]["contents"]
    assert isinstance(contents, list)
    assert [c.role for c in contents] == ["user", "model", "user"]


def test_system_message_maps_to_system_instruction_not_contents() -> None:
    """Unlike OpenAIProvider, Gemini does not accept a "system" role
    inside its message list -- it goes through a separate config field.
    """
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke(
        {
            "messages": [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "hello"},
            ]
        }
    )

    contents = fake.models.calls[0]["contents"]
    assert isinstance(contents, list)
    assert len(contents) == 1
    assert contents[0].role == "user"
    config = fake.models.calls[0]["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.system_instruction == "be terse"


def test_no_system_message_leaves_system_instruction_unset() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    config = fake.models.calls[0]["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.system_instruction is None


def test_successful_completion_uses_default_max_tokens_when_not_given() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    config = fake.models.calls[0]["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.max_output_tokens == 1024


def test_successful_completion_honors_explicit_max_tokens() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    provider.invoke({"messages": [{"role": "user", "content": "hello"}], "max_tokens": 50})

    config = fake.models.calls[0]["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.max_output_tokens == 50


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
        {"messages": [{"role": "narrator", "content": "hello"}]},
        {"messages": [{"role": "system", "content": "only a system message"}]},
    ],
)
def test_invalid_messages_rejected(request_payload: Mapping[str, object]) -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        provider.invoke(request_payload)


def test_more_than_one_system_message_rejected() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        provider.invoke(
            {
                "messages": [
                    {"role": "system", "content": "first"},
                    {"role": "system", "content": "second"},
                    {"role": "user", "content": "hello"},
                ]
            }
        )


@pytest.mark.parametrize("max_tokens", [0, -1, "many", True])
def test_invalid_max_tokens_rejected(max_tokens: Any) -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        provider.invoke(
            {"messages": [{"role": "user", "content": "hello"}], "max_tokens": max_tokens}
        )


# -- authentication failure -----------------------------------------------------


def test_authentication_failure_is_translated() -> None:
    error = _api_error(401, "invalid API key")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiAuthenticationError) as excinfo:
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert "invalid API key" in str(excinfo.value)


def test_forbidden_is_also_translated_as_authentication_failure() -> None:
    error = _api_error(403, "permission denied")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiAuthenticationError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


# -- timeout --------------------------------------------------------------------


def test_timeout_is_translated() -> None:
    error = httpx.ReadTimeout("timed out")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiTimeoutError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


# -- network failure --------------------------------------------------------------


def test_network_failure_is_translated() -> None:
    error = httpx.ConnectError("connection refused")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiConnectionError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_other_api_errors_fall_back_to_the_generic_provider_error() -> None:
    error = _api_error(429, "rate limited")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_server_errors_fall_back_to_the_generic_provider_error() -> None:
    error = errors.ServerError(500, {"error": {"message": "internal error"}})
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_sdk_exceptions_never_escape_the_provider() -> None:
    error = _api_error(401, "invalid API key")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        try:
            provider.invoke({"messages": [{"role": "user", "content": "hello"}]})
        except errors.APIError:
            pytest.fail("a google.genai SDK exception leaked out of GeminiProvider")


def test_httpx_exceptions_never_escape_the_provider() -> None:
    error = httpx.ConnectError("connection refused")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiProviderError):
        try:
            provider.invoke({"messages": [{"role": "user", "content": "hello"}]})
        except httpx.HTTPError:
            pytest.fail("an httpx exception leaked out of GeminiProvider")


# -- malformed / blocked response --------------------------------------------------


def test_response_with_no_text_content_is_translated() -> None:
    empty_response = _make_response("", finish_reason=types.FinishReason.MAX_TOKENS)
    fake = _FakeClient(response=empty_response)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiResponseError, match="MAX_TOKENS"):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_blocked_prompt_is_translated_with_block_reason() -> None:
    fake = _FakeClient(response=_make_blocked_response(types.BlockedReason.SAFETY))
    provider = GeminiProvider(_config(), client=_as_client(fake))

    with pytest.raises(GeminiResponseError, match="SAFETY"):
        provider.invoke({"messages": [{"role": "user", "content": "hello"}]})


def test_missing_usage_metadata_defaults_token_counts_to_zero() -> None:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=[types.Part.from_text(text="hi")]),
        finish_reason=types.FinishReason.STOP,
    )
    response = types.GenerateContentResponse(candidates=[candidate], usage_metadata=None)
    fake = _FakeClient(response=response)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    result = provider.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0


# -- check_health ---------------------------------------------------------------


def test_check_health_reports_healthy_on_success() -> None:
    fake = _FakeClient(response=_make_response())
    provider = GeminiProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is True
    assert report.provider_name == "gemini"


def test_check_health_reports_unhealthy_on_failure() -> None:
    error = _api_error(401, "invalid API key")
    fake = _FakeClient(error=error)
    provider = GeminiProvider(_config(), client=_as_client(fake))

    report = provider.check_health()

    assert report.healthy is False
    assert report.provider_name == "gemini"
    assert "invalid API key" in report.detail
