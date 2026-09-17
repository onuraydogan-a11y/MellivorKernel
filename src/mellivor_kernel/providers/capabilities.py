"""Provider capability description."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Describes what an AI model provider supports.

    Most flags are descriptive metadata: they do not correspond to
    dedicated abstract methods on
    :class:`~mellivor_kernel.providers.base.BaseProvider`. The exception is
    ``supports_tool_calls``, which per ADR-0028 is a contract: a provider
    that sets it reads ``request["tools"]`` and ``request["messages"]`` in
    the provider-neutral shape and returns ``response["tool_calls"]`` (see
    :mod:`mellivor_kernel.providers.tool_calling`), and
    :class:`~mellivor_kernel.execution.tool_loop.ToolCallLoop` refuses a
    provider that does not set it.

    Attributes:
        supports_streaming: Whether the provider can stream partial
            results incrementally.
        supports_tool_calls: Whether the provider forwards offered tools to
            the model and reports the model's tool calls (ADR-0028).
        supports_vision: Whether the provider accepts image/visual input.
        supports_embeddings: Whether the provider can produce vector
            embeddings.
        max_context_tokens: The provider's maximum input context size in
            tokens, if known.
    """

    supports_streaming: bool = False
    supports_tool_calls: bool = False
    supports_vision: bool = False
    supports_embeddings: bool = False
    max_context_tokens: int | None = None
