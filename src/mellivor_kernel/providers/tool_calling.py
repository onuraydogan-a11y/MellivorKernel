"""Provider-neutral tool-calling value types.

These are the shapes a provider consumes and produces when a request
carries tools: a :class:`ToolSpec` describes a tool to the model, a
:class:`ToolCall` is the model's request to invoke one, and a
:class:`ToolResultBlock` carries the outcome back on the next turn.

Nothing here imports a vendor SDK. Each concrete provider translates
between these types and its own wire format; the execution layer's tool
loop (a later change) only ever sees these. Executing a tool is *not* a
provider concern -- a provider returns :class:`ToolCall` values and
stops. Whether and how they run is decided by the execution core, which
keeps authorization and the tool pipeline in the path.

Additive to the v1.x provider contract: :class:`BaseProvider.invoke` keeps
its signature; providers that support tools read ``request["tools"]``
and emit ``response["tool_calls"]``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from mellivor_kernel.providers.exceptions import ProviderError

_EMPTY_OBJECT_SCHEMA: Mapping[str, object] = MappingProxyType({"type": "object"})
"""The JSON Schema for a tool that declares no inputs."""


class ToolCallingError(ProviderError):
    """Raised when a tool-calling value is malformed."""


def _freeze(value: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only view of ``value`` (shallow)."""
    if isinstance(value, MappingProxyType):
        return value
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A tool as described to the model.

    Attributes:
        name: The tool's identifier as the model will refer to it. This is
            the kernel tool id so a returned :class:`ToolCall` can be
            dispatched by name without a lookup table.
        description: What the tool does, in prose the model reads.
        input_schema: A JSON Schema object describing the tool's
            arguments. Defaults to an object with no declared properties;
            consumers should supply a real schema so the model does not
            have to guess argument shapes.
    """

    name: str
    description: str
    input_schema: Mapping[str, object] = field(default=_EMPTY_OBJECT_SCHEMA)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ToolCallingError("ToolSpec.name must not be blank.")
        if not self.description.strip():
            raise ToolCallingError("ToolSpec.description must not be blank.")
        if not isinstance(self.input_schema, Mapping):
            raise ToolCallingError("ToolSpec.input_schema must be a mapping.")
        if self.input_schema.get("type") != "object":
            raise ToolCallingError(
                "ToolSpec.input_schema must be a JSON Schema object (type: 'object')."
            )
        object.__setattr__(self, "input_schema", _freeze(self.input_schema))


@dataclass(frozen=True, slots=True)
class ToolCall:
    """The model's request to invoke a tool.

    Attributes:
        id: The provider-issued identifier for this call. It must be echoed
            in the matching :class:`ToolResultBlock` so the model can pair
            results with requests.
        name: The tool name, matching a :attr:`ToolSpec.name` that was
            offered on the request.
        arguments: The parsed arguments the model supplied.
    """

    id: str
    name: str
    arguments: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ToolCallingError("ToolCall.id must not be blank.")
        if not self.name.strip():
            raise ToolCallingError("ToolCall.name must not be blank.")
        if not isinstance(self.arguments, Mapping):
            raise ToolCallingError("ToolCall.arguments must be a mapping.")
        object.__setattr__(self, "arguments", _freeze(self.arguments))


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    """The outcome of a tool call, sent back to the model.

    Attributes:
        tool_call_id: The :attr:`ToolCall.id` this result answers.
        content: The result rendered as text for the model. Structured
            results are serialized by the caller; the provider does not
            interpret this string.
        is_error: Whether the call failed. Providers that distinguish
            errors on the wire use this; others include it in ``content``.
    """

    tool_call_id: str
    content: str
    is_error: bool = False

    def __post_init__(self) -> None:
        if not self.tool_call_id.strip():
            raise ToolCallingError("ToolResultBlock.tool_call_id must not be blank.")


__all__ = ["ToolCall", "ToolCallingError", "ToolResultBlock", "ToolSpec"]
