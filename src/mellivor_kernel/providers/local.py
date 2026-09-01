"""LocalProvider: text chat through an already-running OpenAI-compatible endpoint.

The adapter never installs, starts, stops, or probes a model runtime implicitly.
Install its optional transport with ``pip install mellivor-kernel[local]``.
See ADR-0026.
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from mellivor_kernel.providers.base import BaseProvider
from mellivor_kernel.providers.capabilities import ProviderCapabilities
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError, ProviderError
from mellivor_kernel.providers.health import ProviderHealthCheck

_DEFAULT_MAX_TOKENS = 1024
_ALLOWED_ROLES = frozenset({"system", "user", "assistant"})
_SUPPORTED_REQUEST_FIELDS = frozenset({"messages", "max_tokens"})
_AUTHENTICATION_STATUS_CODES = frozenset({401, 403})


class LocalProviderError(ProviderError):
    """Base class for errors raised by :class:`LocalProvider`."""


class LocalAuthenticationError(LocalProviderError):
    """Raised when the configured endpoint rejects its optional credential."""


class LocalTimeoutError(LocalProviderError):
    """Raised when the configured endpoint does not respond before the timeout."""


class LocalConnectionError(LocalProviderError):
    """Raised when the configured endpoint cannot be reached."""


class LocalResponseError(LocalProviderError):
    """Raised when the endpoint returns a response the adapter cannot normalize."""


class LocalProvider(BaseProvider):
    """A provider for an explicit, already-running OpenAI-compatible endpoint.

    ``base_url`` and ``default_model`` are required. ``api_key`` is optional
    and, when supplied, is used only as a Bearer token. Construction performs
    no network access.
    """

    def __init__(
        self,
        configuration: ProviderConfiguration,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(configuration)
        if not configuration.default_model or not configuration.default_model.strip():
            raise ProviderConfigurationError("LocalProvider requires configuration.default_model.")
        if not configuration.base_url:
            raise ProviderConfigurationError(
                "LocalProvider requires configuration.base_url for an already-running endpoint."
            )

        self._endpoint = _chat_completions_endpoint(configuration.base_url)
        self._model = configuration.default_model
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if configuration.api_key:
            headers["Authorization"] = f"Bearer {configuration.api_key}"
        self._client = (
            client
            if client is not None
            else httpx.Client(
                timeout=configuration.timeout_seconds,
                headers=headers,
                follow_redirects=False,
                trust_env=False,
            )
        )
        self._headers = headers if client is not None else None

    @property
    def name(self) -> str:
        """Return the registry/factory identifier for this provider."""
        return "local"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Describe the deliberately minimal synchronous text capability."""
        return ProviderCapabilities()

    def check_health(self) -> ProviderHealthCheck:
        """Perform an explicit one-token generation health check; never raise."""
        try:
            self.invoke(
                {
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }
            )
        except LocalProviderError as exc:
            return ProviderHealthCheck(healthy=False, provider_name=self.name, detail=str(exc))
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Generate text through the configured Chat Completions endpoint.

        Supported request keys are ``messages`` and optional ``max_tokens``.
        Messages support only the ``system``, ``user``, and ``assistant``
        roles with text content.
        """
        unknown = sorted(set(request) - _SUPPORTED_REQUEST_FIELDS)
        if unknown:
            raise LocalProviderError(
                f"Unsupported local-provider request field(s): {', '.join(unknown)}."
            )

        messages = _validate_messages(request.get("messages"))
        max_tokens = request.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            raise LocalProviderError(
                "request['max_tokens'] must be a positive integer, if provided."
            )

        response = self._post(
            {
                "model": self._model,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": False,
            }
        )
        if response.status_code in _AUTHENTICATION_STATUS_CODES:
            raise LocalAuthenticationError(
                f"Local inference endpoint rejected the configured credential "
                f"(HTTP {response.status_code})."
            )
        if not response.is_success:
            raise LocalProviderError(
                f"Local inference endpoint request failed with HTTP {response.status_code}."
            )
        return _normalize_response(response)

    def _post(self, payload: Mapping[str, object]) -> httpx.Response:
        attempts = self.configuration.max_retries + 1
        for attempt in range(attempts):
            try:
                return self._client.post(self._endpoint, json=payload, headers=self._headers)
            except httpx.TimeoutException as exc:
                if attempt + 1 == attempts:
                    raise LocalTimeoutError(
                        f"Local inference endpoint timed out after {attempts} attempt(s)."
                    ) from exc
            except httpx.TransportError as exc:
                if attempt + 1 == attempts:
                    raise LocalConnectionError(
                        f"Could not reach local inference endpoint after {attempts} attempt(s)."
                    ) from exc
        raise AssertionError("bounded local-provider retry loop exhausted unexpectedly")


def _chat_completions_endpoint(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ProviderConfigurationError(
            "LocalProvider configuration.base_url must be an absolute HTTP(S) URL."
        )
    if parsed.username is not None or parsed.password is not None:
        raise ProviderConfigurationError(
            "LocalProvider configuration.base_url must not contain user information."
        )
    if parsed.query or parsed.fragment:
        raise ProviderConfigurationError(
            "LocalProvider configuration.base_url must not contain a query or fragment."
        )
    return f"{base_url.rstrip('/')}/chat/completions"


def _validate_messages(messages: object) -> list[dict[str, str]]:
    if not isinstance(messages, list) or not messages:
        raise LocalProviderError("request['messages'] must be a non-empty list.")
    normalized: list[dict[str, str]] = []
    for entry in messages:
        if not isinstance(entry, Mapping):
            raise LocalProviderError("Each entry in request['messages'] must be a mapping.")
        role = entry.get("role")
        content = entry.get("content")
        if not isinstance(role, str) or role not in _ALLOWED_ROLES:
            raise LocalProviderError("Each message role must be one of: system, user, assistant.")
        if not isinstance(content, str):
            raise LocalProviderError("Each message must have string content.")
        normalized.append({"role": role, "content": content})
    return normalized


def _normalize_response(response: httpx.Response) -> Mapping[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise LocalResponseError("Local inference endpoint returned invalid JSON.") from exc
    if not isinstance(payload, Mapping):
        raise LocalResponseError("Local inference endpoint returned a non-object response.")

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
        raise LocalResponseError("Local inference response contained no usable choice.")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
        raise LocalResponseError("Local inference response contained no text content.")
    text = message["content"]
    if not text:
        raise LocalResponseError("Local inference response contained no text content.")

    model = payload.get("model", "")
    if not isinstance(model, str) or not model:
        raise LocalResponseError(
            "Local inference response field 'model' must be a non-empty string."
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise LocalResponseError(
            "Local inference response field 'finish_reason' must be a string or null."
        )

    usage = payload.get("usage", {})
    if usage is None:
        usage = {}
    if not isinstance(usage, Mapping):
        raise LocalResponseError("Local inference response field 'usage' must be an object.")
    prompt_tokens = _token_count(usage.get("prompt_tokens", 0), "prompt_tokens")
    completion_tokens = _token_count(usage.get("completion_tokens", 0), "completion_tokens")
    return {
        "text": text,
        "model": model,
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def _token_count(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise LocalResponseError(
            f"Local inference response usage field {field_name!r} must be a non-negative integer."
        )
    return value
