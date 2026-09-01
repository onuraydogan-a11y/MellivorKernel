"""Experimental direct-HTTP OpenAI-compatible embedding adapter."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from mellivor_kernel.providers._embeddings.contracts import (
    EmbeddingError,
    EmbeddingRequest,
    EmbeddingResult,
    normalize_vector,
)
from mellivor_kernel.providers.configuration import ProviderConfiguration
from mellivor_kernel.providers.exceptions import ProviderConfigurationError
from mellivor_kernel.providers.health import ProviderHealthCheck

_AUTHENTICATION_STATUS_CODES = frozenset({401, 403})


class OpenAICompatibleEmbeddingProvider:
    """Embed text through an explicit OpenAI-compatible HTTP endpoint.

    Experimental and internal per ADR-0027. Construction performs no network
    access. The instance makes no thread-safety guarantee.
    """

    def __init__(
        self,
        configuration: ProviderConfiguration,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        if not configuration.default_model or not configuration.default_model.strip():
            raise ProviderConfigurationError(
                "OpenAICompatibleEmbeddingProvider requires configuration.default_model."
            )
        if not configuration.base_url:
            raise ProviderConfigurationError(
                "OpenAICompatibleEmbeddingProvider requires configuration.base_url."
            )

        self._configuration = configuration
        self._model = configuration.default_model
        self._endpoint = _embeddings_endpoint(configuration.base_url)
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
        """Return the experimental adapter identifier."""
        return "openai-compatible-embedding"

    def check_health(self) -> ProviderHealthCheck:
        """Explicitly embed one synthetic input and translate failure to health."""
        try:
            self.embed(EmbeddingRequest(texts=("health",)))
        except EmbeddingError as exc:
            return ProviderHealthCheck(healthy=False, provider_name=self.name, detail=str(exc))
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed ``request`` while preserving its input order exactly."""
        if not isinstance(request, EmbeddingRequest):
            raise EmbeddingError("Embedding provider requires an EmbeddingRequest.")

        response = self._post({"model": self._model, "input": list(request.texts)})
        if response.status_code in _AUTHENTICATION_STATUS_CODES:
            raise EmbeddingError(
                f"Embedding endpoint rejected the configured credential "
                f"(HTTP {response.status_code})."
            )
        if not response.is_success:
            raise EmbeddingError(
                f"Embedding endpoint request failed with HTTP {response.status_code}."
            )
        return _normalize_response(response, request=request, configured_model=self._model)

    def _post(self, payload: Mapping[str, object]) -> httpx.Response:
        attempts = self._configuration.max_retries + 1
        for attempt in range(attempts):
            try:
                return self._client.post(self._endpoint, json=payload, headers=self._headers)
            except httpx.TimeoutException as exc:
                if attempt + 1 == attempts:
                    raise EmbeddingError(
                        f"Embedding endpoint timed out after {attempts} attempt(s)."
                    ) from exc
            except httpx.TransportError as exc:
                if attempt + 1 == attempts:
                    raise EmbeddingError(
                        f"Could not reach embedding endpoint after {attempts} attempt(s)."
                    ) from exc
        raise AssertionError("bounded embedding retry loop exhausted unexpectedly")


def _embeddings_endpoint(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ProviderConfigurationError(
            "Embedding configuration.base_url must be an absolute HTTP(S) URL."
        )
    if parsed.username is not None or parsed.password is not None:
        raise ProviderConfigurationError(
            "Embedding configuration.base_url must not contain user information."
        )
    if parsed.query or parsed.fragment:
        raise ProviderConfigurationError(
            "Embedding configuration.base_url must not contain a query or fragment."
        )
    return f"{base_url.rstrip('/')}/embeddings"


def _normalize_response(
    response: httpx.Response,
    *,
    request: EmbeddingRequest,
    configured_model: str,
) -> EmbeddingResult:
    try:
        payload = response.json()
    except ValueError as exc:
        raise EmbeddingError("Embedding endpoint returned invalid JSON.") from exc
    if not isinstance(payload, Mapping):
        raise EmbeddingError("Embedding endpoint returned a non-object response.")

    model = payload.get("model")
    if not isinstance(model, str) or not model.strip():
        raise EmbeddingError("Embedding response field 'model' must be a non-blank string.")
    if model != configured_model:
        raise EmbeddingError("Embedding response model did not match the configured model.")

    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(request.texts):
        raise EmbeddingError("Embedding response did not contain one item per input.")

    ordered: list[tuple[float, ...] | None] = [None] * len(request.texts)
    dimensions: int | None = None
    for item in data:
        if not isinstance(item, Mapping):
            raise EmbeddingError("Embedding response items must be objects.")
        index = item.get("index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            or index >= len(ordered)
        ):
            raise EmbeddingError("Embedding response contained an invalid item index.")
        if ordered[index] is not None:
            raise EmbeddingError("Embedding response contained a duplicate item index.")

        vector = normalize_vector(item.get("embedding"), field_name="response vector")
        if dimensions is None:
            dimensions = len(vector)
        elif len(vector) != dimensions:
            raise EmbeddingError("Embedding response vectors had inconsistent dimensions.")
        ordered[index] = vector

    if any(vector is None for vector in ordered) or dimensions is None:
        raise EmbeddingError("Embedding response omitted one or more input indices.")
    vectors = tuple(vector for vector in ordered if vector is not None)
    result = EmbeddingResult(vectors=vectors, model=model, dimensions=dimensions)
    if len(result.vectors) != len(request.texts):
        raise EmbeddingError("Embedding response did not preserve the input batch size.")
    return result
