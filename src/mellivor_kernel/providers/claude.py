"""ClaudeProvider: a BaseProvider implementation backed by the Anthropic
Messages API.

The reference implementation for concrete kernel providers -- it proves
`BaseProvider`'s existing contract requires no changes to support a real
LLM. Scope is deliberately minimal: synchronous request/response, plain
text prompts, plain text responses. No streaming, tool calling, vision,
JSON mode, prompt caching, MCP, or batch execution.

Optional dependency: requires the ``anthropic`` package
(``pip install mellivor-kernel[anthropic]``). This is the only module in
``providers/`` that imports a concrete vendor SDK -- nothing else in the
kernel imports this module or ``anthropic`` itself, so a consumer who
never uses Claude never needs the dependency installed.
"""

from __future__ import annotations

from collections.abc import Mapping

import anthropic

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError, ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck

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

        All ``False``/``None`` beyond the defaults: this sprint's scope is
        synchronous plain-text request/response only.
        """
        return ProviderCapabilities()

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
        """Send a plain text prompt to Claude and return its plain text response.

        Args:
            request: ``{"prompt": str}`` (required); optionally
                ``{"system": str}`` for a system prompt, and
                ``{"max_tokens": int}`` to override the default of
                ``1024``.

        Returns:
            ``{"text": str, "model": str, "stop_reason": str | None,
            "input_tokens": int, "output_tokens": int}``.

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
            ClaudeResponseError: If the response contains no text content.
        """
        prompt = request.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ClaudeProviderError("request['prompt'] must be a non-empty string.")

        system = request.get("system")
        if system is not None and not isinstance(system, str):
            raise ClaudeProviderError("request['system'] must be a string, if provided.")

        max_tokens = request.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise ClaudeProviderError(
                "request['max_tokens'] must be a positive integer, if provided."
            )

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                system=system if system is not None else anthropic.omit,
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
        if not text:
            raise ClaudeResponseError("Anthropic response contained no text content.")

        return {
            "text": text,
            "model": message.model,
            "stop_reason": message.stop_reason,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
