"""Translation between the kernel's provider-neutral message shape and the
OpenAI Chat Completions wire format.

Shared by :class:`~mellivor_kernel.providers.openai.OpenAIProvider` and
:class:`~mellivor_kernel.providers.local.LocalProvider`, which speak the
same format (one through the ``openai`` SDK, one over raw HTTP). Private
to ``providers/``; imports no SDK.

Neutral shape (see :mod:`mellivor_kernel.providers.tool_calling`):

- a message is ``{"role", "content"}`` where content is a string or a
  block list of ``text`` / ``tool_use`` / ``tool_result`` entries;
- ``role`` may be ``system``, ``user`` or ``assistant``.

Chat Completions shape:

- an assistant turn with tool calls carries ``tool_calls`` entries of
  ``{"id", "type": "function", "function": {"name", "arguments": <JSON string>}}``;
- each tool result is its own ``{"role": "tool", "tool_call_id", "content"}``
  message, so one neutral ``tool_result`` user turn fans out into several.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence

from mellivor_kernel.providers.tool_calling import ToolCall, ToolSpec

_ALLOWED_ROLES = frozenset({"system", "user", "assistant"})

ErrorFactory = Callable[[str], Exception]
"""Builds the provider's own request/response error from a message."""


def messages_to_chat(
    messages: object,
    *,
    system: object,
    error: ErrorFactory,
) -> list[dict[str, object]]:
    """Translate ``request["messages"]`` (plus optional ``system``) to
    Chat Completions messages.

    Args:
        messages: The neutral message sequence. Must be a non-empty
            sequence of mappings.
        system: An optional system prompt; prepended as a ``system``
            message when given. ``None`` means not given.
        error: How to build the provider's request error.

    Raises:
        Exception: Whatever ``error`` builds, on malformed input.
    """
    if not isinstance(messages, Sequence) or isinstance(messages, str | bytes) or not messages:
        raise error("request['messages'] must be a non-empty sequence.")
    if system is not None and not isinstance(system, str):
        raise error("request['system'] must be a string, if provided.")
    out: list[dict[str, object]] = []
    if system is not None:
        out.append({"role": "system", "content": system})
    for entry in messages:
        out.extend(_message_to_chat(entry, error))
    return out


def _message_to_chat(entry: object, error: ErrorFactory) -> list[dict[str, object]]:
    if not isinstance(entry, Mapping):
        raise error("Each entry in request['messages'] must be a mapping.")
    role = entry.get("role")
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise error("Each message role must be one of: system, user, assistant.")
    content = entry.get("content")
    if isinstance(content, str):
        return [{"role": role, "content": content}]
    if not isinstance(content, Sequence) or isinstance(content, str | bytes) or not content:
        raise error("Each message must have string content or a non-empty block list.")

    texts: list[str] = []
    tool_calls: list[dict[str, object]] = []
    tool_results: list[dict[str, object]] = []
    for block in content:
        if not isinstance(block, Mapping):
            raise error("Each content block must be a mapping.")
        kind = block.get("type")
        if kind == "text":
            texts.append(str(block.get("text", "")))
        elif kind == "tool_use":
            arguments = block.get("input", {})
            tool_calls.append(
                {
                    "id": str(block.get("id", "")),
                    "type": "function",
                    "function": {
                        "name": str(block.get("name", "")),
                        "arguments": json.dumps(
                            dict(arguments) if isinstance(arguments, Mapping) else {},
                            ensure_ascii=False,
                            default=str,
                        ),
                    },
                }
            )
        elif kind == "tool_result":
            text = str(block.get("content", ""))
            if block.get("is_error"):
                text = f"Error: {text}"
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": str(block.get("tool_call_id", "")),
                    "content": text,
                }
            )
        else:
            raise error(f"Unsupported content block type: {kind!r}.")

    if tool_results:
        if role != "user" or texts or tool_calls:
            raise error("tool_result blocks must be alone in a user message.")
        return tool_results
    if tool_calls:
        if role != "assistant":
            raise error("tool_use blocks are only valid in an assistant message.")
        message: dict[str, object] = {"role": role, "content": "".join(texts) or None}
        message["tool_calls"] = tool_calls
        return [message]
    return [{"role": role, "content": "".join(texts)}]


def tools_to_chat(tools: object, *, error: ErrorFactory) -> list[dict[str, object]] | None:
    """Translate ``request["tools"]`` to Chat Completions function tools.

    Returns ``None`` when no tools were given (or the sequence is empty),
    so callers can omit the parameter entirely.
    """
    if tools is None:
        return None
    if not isinstance(tools, Sequence) or isinstance(tools, str | bytes):
        raise error("request['tools'] must be a sequence of ToolSpec.")
    out: list[dict[str, object]] = []
    for spec in tools:
        if not isinstance(spec, ToolSpec):
            raise error("request['tools'] entries must be ToolSpec instances.")
        out.append(
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": dict(spec.input_schema),
                },
            }
        )
    return out or None


def tool_calls_from_chat(
    raw_calls: object,
    *,
    error: ErrorFactory,
) -> tuple[ToolCall, ...]:
    """Parse a Chat Completions ``message.tool_calls`` value.

    Accepts the SDK's objects (with ``.id`` / ``.function.name`` /
    ``.function.arguments``) or plain dicts of the same shape. Arguments
    arrive as a JSON string; an unparseable string is a response error.
    """
    if raw_calls is None:
        return ()
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, str | bytes):
        raise error("Response field 'tool_calls' must be a list.")
    calls: list[ToolCall] = []
    for raw in raw_calls:
        call_id, name, arguments = _read_call(raw, error)
        try:
            parsed = json.loads(arguments) if arguments.strip() else {}
        except ValueError as exc:
            raise error(f"Tool call {call_id!r} carried non-JSON arguments.") from exc
        if not isinstance(parsed, Mapping):
            raise error(f"Tool call {call_id!r} arguments must be a JSON object.")
        calls.append(ToolCall(id=call_id, name=name, arguments=parsed))
    return tuple(calls)


def _read_call(raw: object, error: ErrorFactory) -> tuple[str, str, str]:
    if isinstance(raw, Mapping):
        call_id = raw.get("id")
        function = raw.get("function")
        name = function.get("name") if isinstance(function, Mapping) else None
        arguments = function.get("arguments") if isinstance(function, Mapping) else None
    else:
        call_id = getattr(raw, "id", None)
        function = getattr(raw, "function", None)
        name = getattr(function, "name", None)
        arguments = getattr(function, "arguments", None)
    if not isinstance(call_id, str) or not call_id:
        raise error("Each tool call must carry a non-empty string 'id'.")
    if not isinstance(name, str) or not name:
        raise error(f"Tool call {call_id!r} must carry a function name.")
    if arguments is None:
        arguments = ""
    if not isinstance(arguments, str):
        raise error(f"Tool call {call_id!r} arguments must be a JSON string.")
    return call_id, name, arguments


__all__ = ["messages_to_chat", "tool_calls_from_chat", "tools_to_chat"]
