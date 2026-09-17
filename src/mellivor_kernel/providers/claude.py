"""ClaudeProvider: a BaseProvider implementation backed by the Anthropic
Messages API.

The reference implementation for concrete kernel providers -- it proves
`BaseProvider`'s existing contract requires no changes to support a real
LLM. Scope: synchronous request/response, plain text prompts or a
message list, plain text responses, and tool calling (the provider
describes tools and reports the model's calls; it never executes them --
see :mod:`mellivor_kernel.providers.tool_calling`). No streaming, vision,
JSON mode, prompt caching, MCP, or batch execution.

Optional dependency: requires the ``anthropic`` package
(``pip install mellivor-kernel[anthropic]``). This is the only module in
``providers/`` that imports a concrete vendor SDK -- nothing else in the
kernel imports this module or ``anthropic`` itself, so a consumer who
never uses Claude never needs the dependency installed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

import anthropic
from anthropic.types import MessageParam, ToolParam

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError, ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck
from mellivor_kernel.providers.tool_calling import ToolCall, ToolSpec

_DEFAULT_MAX_TOKENS = 1024
"""Anthropic's Messages API requires ``max_tokens`` on every request. The
kernel's minimal "plain text prompt" request shape has no natural place
for it, so this is the default when a caller doesn't supply one via
``request["max_tokens"]`` -- a per-request fallback constant, not global
configuration.
"""


class ClaudeProviderError(ProviderError):
    """Base class for errors raised by :class:`ClaudeProvider`."""


class ClaudeAuthenticationError(ClaudeProviderError):
    """Raised when the Anthropic API rejects the configured credentials."""


class ClaudeTimeoutError(ClaudeProviderError):
    """Raised when a request to the Anthropic API times out."""


class ClaudeConnectionError(ClaudeProviderError):
    """Raised when a request to the Anthropic API cannot be completed due to a network failure."""


class ClaudeResponseError(ClaudeProviderError):
    """Raised when the Anthropic API returns a response this provider cannot interpret."""


class ClaudeProvider(BaseProvider):
    """A :class:`~mellivor_kernel.providers.base.BaseProvider` implementation
    backed by the Anthropic Messages API.

    Configuration is read only from the kernel's existing
    :class:`~mellivor_kernel.providers.configuration.ProviderConfiguration`
    -- no provider-specific global configuration (no reading
    ``ANTHROPIC_API_KEY`` or any other environment variable) is
    introduced. ``api_key`` and ``default_model`` are required at
    construction; ``base_url``, ``timeout_seconds``, and ``max_retries``
    are passed through to the Anthropic client as given.
    """

    def __init__(
        self,
        configuration: ProviderConfiguration,
        *,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            configuration: The kernel configuration to construct this
                provider from. ``api_key`` and ``default_model`` must both
                be set.
            client: An already-constructed Anthropic client. Constructed
                automatically from ``configuration`` if not provided --
                the seam tests use to inject a fake client, so unit tests
                never touch the network.

        Raises:
            ProviderConfigurationError: If ``configuration.api_key`` or
                ``configuration.default_model`` is not set. ``api_key`` is
                required explicitly rather than left to the Anthropic
                client's own fallback to the ``ANTHROPIC_API_KEY`` environment
                variable -- that fallback would be exactly the
                provider-specific global configuration this sprint's scope
                excludes.
        """
        super().__init__(configuration)
        if not configuration.api_key:
            raise ProviderConfigurationError(
                "ClaudeProvider requires configuration.api_key. It does not fall back to the "
                "ANTHROPIC_API_KEY environment variable, so credentials always flow through the "
                "kernel's own configuration system."
            )
        if not configuration.default_model:
            raise ProviderConfigurationError(
                "ClaudeProvider requires configuration.default_model (e.g. 'claude-sonnet-5')."
            )

        self._model = configuration.default_model
        self._client = (
            client
            if client is not None
            else anthropic.Anthropic(
                api_key=configuration.api_key,
                base_url=configuration.base_url,
                timeout=configuration.timeout_seconds,
                max_retries=configuration.max_retries,
            )
        )

    @property
    def name(self) -> str:
        """A short, unique identifier for this provider."""
        return "claude"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """The capabilities this provider supports.

        ``supports_tool_calls`` is ``True``: :meth:`invoke` forwards
        ``request["tools"]`` to the model and reports its calls in
        ``response["tool_calls"]``. Everything else stays at the defaults.
        """
        return ProviderCapabilities(supports_tool_calls=True)

    def check_health(self) -> ProviderHealthCheck:
        """Check whether the Anthropic API is currently reachable and usable.

        Issues a minimal real request (``max_tokens=1``) through the same
        client and error handling :meth:`invoke` uses.

        Returns:
            A healthy :class:`ProviderHealthCheck` if the request succeeds.
            An unhealthy one, with the failure's detail, otherwise --
            never raises.
        """
        try:
            self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        except anthropic.AnthropicError as exc:
            return ProviderHealthCheck(healthy=False, provider_name=self.name, detail=str(exc))
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Send a prompt or a conversation to Claude and return its response.

        Args:
            request: Exactly one of ``{"prompt": str}`` (a single user
                turn) or ``{"messages": [...]}`` (a conversation in the
                provider-neutral shape: each message has ``role`` and
                ``content``, where content is a string or a sequence of
                ``text``/``tool_use``/``tool_result`` blocks). Optionally
                ``{"system": str}``, ``{"max_tokens": int}`` (default
                ``1024``), and ``{"tools": [ToolSpec, ...]}`` to offer
                tools the model may call.

        Returns:
            ``{"text": str, "tool_calls": tuple[ToolCall, ...], "model": str,
            "stop_reason": str | None, "input_tokens": int,
            "output_tokens": int}``. ``text`` is the concatenated text
            content and may be empty when the model only asked for tools;
            ``tool_calls`` is empty when it did not.

        Raises:
            ClaudeProviderError: If ``request`` is malformed, or for any
                Anthropic API failure not covered by a more specific
                exception below -- never an ``anthropic`` SDK exception
                directly.
            ClaudeAuthenticationError: If the Anthropic API rejects the
                configured credentials.
            ClaudeTimeoutError: If the request times out.
            ClaudeConnectionError: If the request cannot be completed due
                to a network failure.
            ClaudeResponseError: If the response contains neither text nor
                a tool call.
        """
        messages = self._messages_from(request)
        system = request.get("system")
        if system is not None and not isinstance(system, str):
            raise ClaudeProviderError("request['system'] must be a string, if provided.")
        max_tokens = request.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise ClaudeProviderError(
                "request['max_tokens'] must be a positive integer, if provided."
            )
        tools = self._tools_from(request)

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=cast(list[MessageParam], messages),
                system=system if system is not None else anthropic.omit,
                tools=cast(list[ToolParam], tools) if tools is not None else anthropic.omit,
            )
        except anthropic.AuthenticationError as exc:
            raise ClaudeAuthenticationError(
                f"Anthropic API rejected the configured credentials: {exc}"
            ) from exc
        except anthropic.APITimeoutError as exc:
            raise ClaudeTimeoutError(f"Request to the Anthropic API timed out: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise ClaudeConnectionError(f"Could not reach the Anthropic API: {exc}") from exc
        except anthropic.AnthropicError as exc:
            raise ClaudeProviderError(f"Anthropic API request failed: {exc}") from exc

        text = "".join(
            block.text for block in message.content if isinstance(block, anthropic.types.TextBlock)
        )
        tool_calls = tuple(
            ToolCall(
                id=block.id,
                name=block.name,
                arguments=block.input if isinstance(block.input, Mapping) else {},
            )
            for block in message.content
            if isinstance(block, anthropic.types.ToolUseBlock)
        )
        if not text and not tool_calls:
            raise ClaudeResponseError("Anthropic response contained no text content.")
        return {
            "text": text,
            "tool_calls": tool_calls,
            "model": message.model,
            "stop_reason": message.stop_reason,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }

    @staticmethod
    def _messages_from(request: Mapping[str, object]) -> list[dict[str, object]]:
        """Resolve ``prompt`` or ``messages`` into Anthropic message dicts."""
        prompt = request.get("prompt")
        messages = request.get("messages")
        if prompt is not None and messages is not None:
            raise ClaudeProviderError("request must carry either 'prompt' or 'messages', not both.")
        if messages is None:
            if not isinstance(prompt, str) or not prompt.strip():
                raise ClaudeProviderError("request['prompt'] must be a non-empty string.")
            return [{"role": "user", "content": prompt}]
        if not isinstance(messages, Sequence) or isinstance(messages, str | bytes) or not messages:
            raise ClaudeProviderError("request['messages'] must be a non-empty sequence.")
        return [_to_anthropic_message(entry) for entry in messages]

    @staticmethod
    def _tools_from(request: Mapping[str, object]) -> list[dict[str, object]] | None:
        """Resolve ``tools`` into Anthropic tool definitions, if offered."""
        tools = request.get("tools")
        if tools is None:
            return None
        if not isinstance(tools, Sequence) or isinstance(tools, str | bytes):
            raise ClaudeProviderError("request['tools'] must be a sequence of ToolSpec.")
        definitions: list[dict[str, object]] = []
        for spec in tools:
            if not isinstance(spec, ToolSpec):
                raise ClaudeProviderError("request['tools'] entries must be ToolSpec instances.")
            definitions.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "input_schema": dict(spec.input_schema),
                }
            )
        return definitions or None


def _to_anthropic_message(entry: object) -> dict[str, object]:
    """Translate one provider-neutral message into the Anthropic wire shape."""
    if not isinstance(entry, Mapping):
        raise ClaudeProviderError("each message must be a mapping with 'role' and 'content'.")
    role = entry.get("role")
    if role not in ("user", "assistant"):
        raise ClaudeProviderError("message['role'] must be 'user' or 'assistant'.")
    content = entry.get("content")
    if isinstance(content, str):
        if not content.strip():
            raise ClaudeProviderError("message['content'] must not be blank.")
        return {"role": role, "content": content}
    if not isinstance(content, Sequence) or isinstance(content, str | bytes) or not content:
        raise ClaudeProviderError("message['content'] must be a string or a non-empty block list.")
    return {"role": role, "content": [_to_anthropic_block(block) for block in content]}


def _to_anthropic_block(block: object) -> dict[str, object]:
    if not isinstance(block, Mapping):
        raise ClaudeProviderError("each content block must be a mapping.")
    kind = block.get("type")
    if kind == "text":
        return {"type": "text", "text": str(block.get("text", ""))}
    if kind == "tool_use":
        arguments = block.get("input", {})
        return {
            "type": "tool_use",
            "id": str(block.get("id", "")),
            "name": str(block.get("name", "")),
            "input": dict(arguments) if isinstance(arguments, Mapping) else {},
        }
    if kind == "tool_result":
        result: dict[str, object] = {
            "type": "tool_result",
            "tool_use_id": str(block.get("tool_call_id", "")),
            "content": str(block.get("content", "")),
        }
        if block.get("is_error"):
            result["is_error"] = True
        return result
    raise ClaudeProviderError(f"unsupported content block type: {kind!r}.")
