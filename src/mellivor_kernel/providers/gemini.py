"""GeminiProvider: a BaseProvider implementation backed by the Gemini
Developer API.

The kernel's third concrete provider -- proves `BaseProvider`'s existing
contract generalizes to a genuinely different vendor SDK shape (`google-genai`'s
`.code`-based error model, `httpx`-transport-level failures the SDK does
not wrap itself, and a config-nested credential/timeout shape), not a
third copy of `ClaudeProvider`'s or `OpenAIProvider`'s SDK-integration
pattern. Scope is deliberately minimal: synchronous request/response,
plain message-list prompts (reusing `OpenAIProvider`'s request/response
key names -- see ADR-0023), plain text responses. No streaming, tool
calling, vision, multimodal input, Vertex AI authentication, or batch
execution.

Optional dependency: requires the ``google-genai`` package
(``pip install mellivor-kernel[gemini]``). This is the only module in
``providers/`` that imports ``google.genai`` -- nothing else in the
kernel imports this module or the SDK, so a consumer who never uses
Gemini never needs the dependency installed. See
`ADR-0023 <../../docs/adr/0023-gemini-provider.md>`_ for the full design
rationale, including why ``google-genai`` (not the deprecated
``google-generativeai`` package) was selected.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import httpx
from google import genai
from google.genai import errors, types

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError, ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck

_DEFAULT_MAX_TOKENS = 1024
"""Not required by the Gemini API itself, but applied here for the same
reason `providers.claude._DEFAULT_MAX_TOKENS` and
`providers.openai._DEFAULT_MAX_TOKENS` exist: a bounded default when a
caller doesn't supply one via ``request["max_tokens"]``.
"""

_ROLE_MAP = {"user": "user", "assistant": "model"}
"""Gemini's own vocabulary for a model turn is ``"model"``, not
``"assistant"`` -- the one true role-name translation this provider
performs. ``"user"`` passes through unchanged. See ADR-0023's "Request
translation / role-message mapping".
"""

_AUTHENTICATION_STATUS_CODES = frozenset({401, 403})


class GeminiProviderError(ProviderError):
    """Base class for errors raised by :class:`GeminiProvider`."""


class GeminiAuthenticationError(GeminiProviderError):
    """Raised when the Gemini API rejects the configured credentials."""


class GeminiTimeoutError(GeminiProviderError):
    """Raised when a request to the Gemini API times out."""


class GeminiConnectionError(GeminiProviderError):
    """Raised when a request to the Gemini API cannot be completed due to a network failure."""


class GeminiResponseError(GeminiProviderError):
    """Raised when the Gemini API returns a response this provider cannot interpret.

    Also raised when Gemini blocks a prompt or a candidate for safety
    reasons -- this is a case of "no usable text content," the same
    scope :class:`~mellivor_kernel.providers.claude.ClaudeResponseError`/
    :class:`~mellivor_kernel.providers.openai.OpenAIResponseError`
    already have; see ADR-0023's "Safety/filter response handling."
    """


class GeminiProvider(BaseProvider):
    """A :class:`~mellivor_kernel.providers.base.BaseProvider` implementation
    backed by the Gemini Developer API.

    Configuration is read only from the kernel's existing
    :class:`~mellivor_kernel.providers.configuration.ProviderConfiguration`
    -- no provider-specific global configuration (no reading
    ``GOOGLE_API_KEY``/``GEMINI_API_KEY`` or any other environment
    variable) is introduced. ``api_key`` and ``default_model`` are
    required at construction; ``base_url``, ``timeout_seconds``, and
    ``max_retries`` are passed through to the ``google-genai`` client's
    ``http_options`` as given.

    Gemini Developer API authentication only (``api_key``) -- Vertex
    AI's project/location-based authentication is not supported; see
    ADR-0023's "Credential handling."
    """

    def __init__(
        self,
        configuration: ProviderConfiguration,
        *,
        client: genai.Client | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            configuration: The kernel configuration to construct this
                provider from. ``api_key`` and ``default_model`` must both
                be set.
            client: An already-constructed ``google-genai`` client.
                Constructed automatically from ``configuration`` if not
                provided -- the seam tests use to inject a fake client, so
                unit tests never touch the network.

        Raises:
            ProviderConfigurationError: If ``configuration.api_key`` or
                ``configuration.default_model`` is not set. ``api_key`` is
                required explicitly rather than left to the SDK's own
                fallback to the ``GOOGLE_API_KEY``/``GEMINI_API_KEY``
                environment variables -- that fallback would be exactly
                the provider-specific global configuration this sprint's
                scope excludes.
        """
        super().__init__(configuration)
        if not configuration.api_key:
            raise ProviderConfigurationError(
                "GeminiProvider requires configuration.api_key. It does not fall back to the "
                "GOOGLE_API_KEY/GEMINI_API_KEY environment variables, so credentials always flow "
                "through the kernel's own configuration system."
            )
        if not configuration.default_model:
            raise ProviderConfigurationError(
                "GeminiProvider requires configuration.default_model (e.g. 'gemini-2.0-flash-001')."
            )

        self._model = configuration.default_model
        self._client = (
            client
            if client is not None
            else genai.Client(
                api_key=configuration.api_key,
                http_options=types.HttpOptions(
                    base_url=configuration.base_url,
                    timeout=int(configuration.timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=configuration.max_retries),
                ),
            )
        )

    @property
    def name(self) -> str:
        """A short, unique identifier for this provider."""
        return "gemini"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """The capabilities this provider supports.

        All ``False``/``None`` beyond the defaults: this sprint's scope is
        synchronous plain-text request/response only.
        """
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        """Check whether the Gemini API is currently reachable and usable.

        Issues a minimal real request (``max_output_tokens=1``) through
        the same client and error handling :meth:`invoke` uses.

        Returns:
            A healthy :class:`ProviderHealthCheck` if the request succeeds.
            An unhealthy one, with the failure's detail, otherwise --
            never raises.
        """
        try:
            self._client.models.generate_content(
                model=self._model,
                contents=cast(
                    "Any",
                    [types.Content(role="user", parts=[types.Part.from_text(text="ping")])],
                ),
                config=types.GenerateContentConfig(max_output_tokens=1),
            )
        except (errors.APIError, httpx.TimeoutException, httpx.TransportError) as exc:
            return ProviderHealthCheck(healthy=False, provider_name=self.name, detail=str(exc))
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Send a multi-turn message list to Gemini and return its plain text response.

        Args:
            request: ``{"messages": list[{"role": str, "content": str}]}``
                (required, non-empty; ``role`` is one of ``"system"``
                (at most one, mapped to Gemini's ``system_instruction``),
                ``"user"``, or ``"assistant"`` (mapped to Gemini's own
                ``"model"`` role)); optionally ``{"max_tokens": int}`` to
                override the default of ``1024``.

        Returns:
            ``{"text": str, "model": str, "finish_reason": str | None,
            "prompt_tokens": int, "completion_tokens": int}``.

        Raises:
            GeminiProviderError: If ``request`` is malformed, or for any
                Gemini API failure not covered by a more specific
                exception below -- never a ``google.genai``/``httpx``
                exception directly.
            GeminiAuthenticationError: If the Gemini API rejects the
                configured credentials.
            GeminiTimeoutError: If the request times out.
            GeminiConnectionError: If the request cannot be completed due
                to a network failure.
            GeminiResponseError: If the response (or the prompt itself)
                contains no text content, including a safety-filtered
                block.
        """
        contents, system_instruction = self._translate_messages(request.get("messages"))

        max_tokens = request.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise GeminiProviderError(
                "request['max_tokens'] must be a positive integer, if provided."
            )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=cast("Any", contents),
                config=config,
            )
        except errors.APIError as exc:
            if exc.code in _AUTHENTICATION_STATUS_CODES:
                raise GeminiAuthenticationError(
                    f"Gemini API rejected the configured credentials: {exc}"
                ) from exc
            raise GeminiProviderError(f"Gemini API request failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise GeminiTimeoutError(f"Request to the Gemini API timed out: {exc}") from exc
        except httpx.TransportError as exc:
            raise GeminiConnectionError(f"Could not reach the Gemini API: {exc}") from exc

        text = response.text
        if not text:
            if not response.candidates:
                block_reason = (
                    response.prompt_feedback.block_reason if response.prompt_feedback else None
                )
                raise GeminiResponseError(
                    "Gemini blocked the prompt before generating a response "
                    f"(block_reason={block_reason.value if block_reason else None})."
                )
            finish_reason = response.candidates[0].finish_reason
            raise GeminiResponseError(
                "Gemini response contained no text content "
                f"(finish_reason={finish_reason.value if finish_reason else None})."
            )

        if not response.candidates:
            # Unreachable in practice: `response.text` above already guarantees
            # at least one candidate with text parts exists when truthy. Kept
            # as an explicit, narrowing check rather than an `assert`, so a
            # future SDK behavior change fails loudly instead of crashing.
            raise GeminiResponseError(
                "Gemini response contained text but no candidates -- unexpected SDK response shape."
            )
        candidate = response.candidates[0]
        finish_reason_value = candidate.finish_reason.value if candidate.finish_reason else None
        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage and usage.prompt_token_count else 0
        completion_tokens = (
            usage.candidates_token_count if usage and usage.candidates_token_count else 0
        )

        return {
            "text": text,
            "model": self._model,
            "finish_reason": finish_reason_value,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def _translate_messages(self, messages: object) -> tuple[list[types.Content], str | None]:
        """Validate and translate `request["messages"]` into Gemini's shape.

        Returns:
            A tuple of ``(contents, system_instruction)``, ready to pass
            to ``generate_content``.

        Raises:
            GeminiProviderError: If `messages` is missing, empty, not a
                list, any entry is malformed, any entry's role is not
                `"system"`/`"user"`/`"assistant"`, more than one
                `"system"`-role entry is present, or no non-system
                message remains after mapping.
        """
        if not isinstance(messages, list) or not messages:
            raise GeminiProviderError("request['messages'] must be a non-empty list.")

        system_parts: list[str] = []
        contents: list[types.Content] = []
        for entry in messages:
            if not isinstance(entry, Mapping):
                raise GeminiProviderError("Each entry in request['messages'] must be a mapping.")
            role = entry.get("role")
            content = entry.get("content")
            if not isinstance(role, str) or not role.strip():
                raise GeminiProviderError(
                    "Each entry in request['messages'] must have a non-empty string 'role'."
                )
            if not isinstance(content, str):
                raise GeminiProviderError(
                    "Each entry in request['messages'] must have a string 'content'."
                )
            if role == "system":
                system_parts.append(content)
                continue
            gemini_role = _ROLE_MAP.get(role)
            if gemini_role is None:
                raise GeminiProviderError(
                    f"request['messages'] role {role!r} is not supported; "
                    "expected 'system', 'user', or 'assistant'."
                )
            contents.append(
                types.Content(role=gemini_role, parts=[types.Part.from_text(text=content)])
            )

        if len(system_parts) > 1:
            raise GeminiProviderError(
                "request['messages'] must include at most one message with role 'system'."
            )
        if not contents:
            raise GeminiProviderError(
                "request['messages'] must include at least one non-system message."
            )

        system_instruction = system_parts[0] if system_parts else None
        return contents, system_instruction
