"""Provider capability description."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Describes what an AI model provider supports.

    These flags are descriptive metadata only in this sprint: they do not
    yet correspond to dedicated abstract methods on
    :class:`~mellivor_kernel.providers.base.BaseProvider` (for example, a
    dedicated streaming API). That refinement is left for when a real
    provider informs the actual shape of that behavior.

    Attributes:
        supports_streaming: Whether the provider can stream partial
            results incrementally.
        supports_tool_calls: Whether the provider supports invoking
            external tools/functions as part of a response.
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
