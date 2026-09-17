"""OpenAIProvider: a BaseProvider implementation backed by the OpenAI Chat
Completions API.

The kernel's second concrete provider -- proves `BaseProvider`'s existing
contract generalizes to a genuinely different request shape than
`ClaudeProvider`'s (a multi-turn message list, not a flat prompt string),
not a second copy of it. Scope is deliberately minimal: synchronous
request/response, plain message-list prompts, plain text responses. No
streaming, tool calling, vision, JSON mode, function calling, prompt
caching, or batch execution.

Optional dependency: requires the ``openai`` package
(``pip install mellivor-kernel[openai]``). This is the only module in
``providers/`` that imports this vendor SDK -- nothing else in the
kernel imports this module or ``openai`` itself, so a consumer who never
uses OpenAI never needs the dependency installed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from mellivor_kernel.providers._chat_completions import (
    messages_to_chat,
    tool_calls_from_chat,
    tools_to_chat,
)
from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError, ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck

_DEFAULT_MAX_TOKENS = 1024
"""Not required by the OpenAI API itself, but applied here for the same
reason `providers.claude._DEFAULT_MAX_TOKENS` exists: a bounded default
when a caller doesn't supply one via ``request["max_tokens"]``, a
per-request fallback constant, not global configuration.
"""


class OpenAIProviderError(ProviderError):
    """Base class for errors raised by :class:`OpenAIProvider`."""


class OpenAIAuthenticationError(OpenAIProviderError):
    """Raised when the OpenAI API rejects the configured credentials."""


class OpenAITimeoutError(OpenAIProviderError):
    """Raised when a request to the OpenAI API times out."""


class OpenAIConnectionError(OpenAIProviderError):
    """Raised when a request to the OpenAI API cannot be completed due to a network failure."""


class OpenAIResponseError(OpenAIProviderError):
    """Raised when the OpenAI API returns a response this provider cannot interpret."""


class OpenAIProvider(BaseProvider):
    """A :class:`~mellivor_kernel.providers.base.BaseProvider` implementation
    backed by the OpenAI Chat Completions API.

    Configuration is read only from the kernel's existing
    :class:`~mellivor_kernel.providers.configuration.ProviderConfiguration`
    -- no provider-specific global configuration (no reading
    ``OPENAI_API_KEY`` or any other environment variable) is introduced.
    ``api_key`` and ``default_model`` are required at construction;
    ``base_url``, ``timeout_seconds``, and ``max_retries`` are passed
    through to the OpenAI client as given.
    """

    def __init__(
        self,
        configuration: ProviderConfiguration,
        *,
        client: openai.OpenAI | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            configuration: The kernel configuration to construct this
                provider from. ``api_key`` and ``default_model`` must both
                be set.
            client: An already-constructed OpenAI client. Constructed
                automatically from ``configuration`` if not provided --
                the seam tests use to inject a fake client, so unit tests
                never touch the network.

        Raises:
            ProviderConfigurationError: If ``configuration.api_key`` or
                ``configuration.default_model`` is not set. ``api_key`` is
                required explicitly rather than left to the OpenAI
                client's own fallback to the ``OPENAI_API_KEY`` environment
                variable -- that fallback would be exactly the
                provider-specific global configuration this sprint's scope
                excludes.
        """
        super().__init__(configuration)
        if not configuration.api_key:
            raise ProviderConfigurationError(
                "OpenAIProvider requires configuration.api_key. It does not fall back to the "
                "OPENAI_API_KEY environment variable, so credentials always flow through the "
                "kernel's own configuration system."
            )
        if not configuration.default_model:
            raise ProviderConfigurationError(
                "OpenAIProvider requires configuration.default_model (e.g. 'gpt-4o')."
            )

        self._model = configuration.default_model
        self._client = (
            client
            if client is not None
            else openai.OpenAI(
                api_key=configuration.api_key,
                base_url=configuration.base_url,
                timeout=configuration.timeout_seconds,
                max_retries=configuration.max_retries,
            )
        )

    @property
    def name(self) -> str:
        """A short, unique identifier for this provider."""
        return "openai"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """The capabilities this provider supports.

        ``supports_tool_calls`` is ``True``: :meth:`invoke` forwards
        ``request["tools"]`` as function tools and reports the model's
        calls in ``response["tool_calls"]``.
        """
        return ProviderCapabilities(supports_tool_calls=True)

    def check_health(self) -> ProviderHealthCheck:
        """Check whether the OpenAI API is currently reachable and usable.

        Issues a minimal real request (``max_tokens=1``) through the same
        client and error handling :meth:`invoke` uses.

        Returns:
            A healthy :class:`ProviderHealthCheck` if the request succeeds.
            An unhealthy one, with the failure's detail, otherwise --
            never raises.
        """
        try:
            self._client.chat.completions.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        except openai.OpenAIError as exc:
            return ProviderHealthCheck(healthy=False, provider_name=self.name, detail=str(exc))
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Send a message list to OpenAI and return its response.

        Args:
            request: ``{"messages": [...]}`` (required, non-empty): a
                conversation in the provider-neutral shape -- each message
                has ``role`` (``system``/``user``/``assistant``) and
                ``content``, a string or a block list of
                ``text``/``tool_use``/``tool_result`` entries. Optionally
                ``{"system": str}`` (prepended as a system message),
                ``{"max_tokens": int}`` (default ``1024``), and
                ``{"tools": [ToolSpec, ...]}`` to offer function tools.

        Returns:
            ``{"text": str, "tool_calls": tuple[ToolCall, ...], "model": str,
            "finish_reason": str | None, "prompt_tokens": int,
            "completion_tokens": int}``. ``text`` may be empty when the
            model only asked for tools.

        Raises:
            OpenAIProviderError: If ``request`` is malformed, or for any
                OpenAI API failure not covered by a more specific
                exception below -- never an ``openai`` SDK exception
                directly.
            OpenAIAuthenticationError: If the OpenAI API rejects the
                configured credentials.
            OpenAITimeoutError: If the request times out.
            OpenAIConnectionError: If the request cannot be completed due
                to a network failure.
            OpenAIResponseError: If the response contains neither text nor
                a tool call, or a tool call cannot be parsed.
        """
        messages = messages_to_chat(
            request.get("messages"), system=request.get("system"), error=OpenAIProviderError
        )
        max_tokens = request.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise OpenAIProviderError(
                "request['max_tokens'] must be a positive integer, if provided."
            )
        tools = tools_to_chat(request.get("tools"), error=OpenAIProviderError)

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=cast("list[ChatCompletionMessageParam]", messages),
                tools=cast("list[ChatCompletionToolParam]", tools)
                if tools is not None
                else openai.omit,
            )
        except openai.AuthenticationError as exc:
            raise OpenAIAuthenticationError(
                f"OpenAI API rejected the configured credentials: {exc}"
            ) from exc
        except openai.APITimeoutError as exc:
            raise OpenAITimeoutError(f"Request to the OpenAI API timed out: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise OpenAIConnectionError(f"Could not reach the OpenAI API: {exc}") from exc
        except openai.OpenAIError as exc:
            raise OpenAIProviderError(f"OpenAI API request failed: {exc}") from exc

        choice = completion.choices[0]
        text = choice.message.content or ""
        tool_calls = tool_calls_from_chat(choice.message.tool_calls, error=OpenAIResponseError)
        if not text and not tool_calls:
            raise OpenAIResponseError("OpenAI response contained no text content.")
        return {
            "text": text,
            "tool_calls": tool_calls,
            "model": completion.model,
            "finish_reason": choice.finish_reason,
            "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
            "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
        }
