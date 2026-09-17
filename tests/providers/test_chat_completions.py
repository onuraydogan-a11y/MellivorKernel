"""Tests for mellivor_kernel.providers._chat_completions (SDK-free)."""

from __future__ import annotations

import json

import pytest

from mellivor_kernel.providers import ToolCall, ToolSpec, assistant_message, tool_results_message
from mellivor_kernel.providers._chat_completions import (
    messages_to_chat,
    tool_calls_from_chat,
    tools_to_chat,
)
from mellivor_kernel.providers.tool_calling import ToolResultBlock


class _Err(Exception):
    pass


def test_string_messages_pass_through_and_system_is_prepended() -> None:
    out = messages_to_chat([{"role": "user", "content": "hi"}], system="be terse", error=_Err)

    assert out == [{"role": "system", "content": "be terse"}, {"role": "user", "content": "hi"}]


def test_neutral_round_trip_becomes_chat_completions_shape() -> None:
    call = ToolCall(id="c1", name="echo", arguments={"message": "x"})
    history = [
        {"role": "user", "content": "hi"},
        assistant_message("checking", [call]),
        tool_results_message([ToolResultBlock(tool_call_id="c1", content="ok")]),
    ]

    out = messages_to_chat(history, system=None, error=_Err)

    assert out[0] == {"role": "user", "content": "hi"}
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "checking"
    assert out[1]["tool_calls"] == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "echo", "arguments": '{"message": "x"}'},
        }
    ]
    assert out[2] == {"role": "tool", "tool_call_id": "c1", "content": "ok"}


def test_tool_only_assistant_turn_has_null_content_and_errors_are_prefixed() -> None:
    history = [
        assistant_message("", [ToolCall(id="c1", name="echo")]),
        tool_results_message([ToolResultBlock(tool_call_id="c1", content="nope", is_error=True)]),
    ]

    out = messages_to_chat(history, system=None, error=_Err)

    assert out[0]["content"] is None
    assert out[1]["content"] == "Error: nope"


def test_two_results_fan_out_into_two_tool_messages() -> None:
    history = [
        tool_results_message(
            [
                ToolResultBlock(tool_call_id="a", content="1"),
                ToolResultBlock(tool_call_id="b", content="2"),
            ]
        )
    ]

    out = messages_to_chat(history, system=None, error=_Err)

    assert [m["tool_call_id"] for m in out] == ["a", "b"]


@pytest.mark.parametrize(
    ("messages", "system"),
    [
        ([], None),
        ("nope", None),
        (["bad"], None),
        ([{"role": "tool", "content": "x"}], None),
        ([{"role": "user", "content": 1}], None),
        ([{"role": "user", "content": []}], None),
        ([{"role": "user", "content": [{"type": "image"}]}], None),
        ([{"role": "user", "content": [{"type": "tool_use", "id": "c", "name": "e"}]}], None),
        ([{"role": "assistant", "content": [{"type": "tool_result", "tool_call_id": "c"}]}], None),
        ([{"role": "user", "content": "x"}], 1),
    ],
)
def test_malformed_messages_raise_the_given_error(messages: object, system: object) -> None:
    with pytest.raises(_Err):
        messages_to_chat(messages, system=system, error=_Err)


def test_tools_to_chat_builds_function_tools_and_omits_when_empty() -> None:
    spec = ToolSpec(
        name="echo",
        description="Echo.",
        input_schema={"type": "object", "properties": {"m": {"type": "string"}}},
    )

    assert tools_to_chat([spec], error=_Err) == [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo.",
                "parameters": {"type": "object", "properties": {"m": {"type": "string"}}},
            },
        }
    ]
    assert tools_to_chat(None, error=_Err) is None
    assert tools_to_chat([], error=_Err) is None
    with pytest.raises(_Err):
        tools_to_chat("echo", error=_Err)
    with pytest.raises(_Err):
        tools_to_chat([{"name": "echo"}], error=_Err)


def test_tool_calls_from_chat_parses_dicts_and_objects() -> None:
    class _Fn:
        name = "echo"
        arguments = json.dumps({"message": "x"})

    class _Obj:
        id = "c2"
        function = _Fn()

    raw = [{"id": "c1", "function": {"name": "echo", "arguments": '{"message": "y"}'}}, _Obj()]

    calls = tool_calls_from_chat(raw, error=_Err)

    assert calls == (
        ToolCall(id="c1", name="echo", arguments={"message": "y"}),
        ToolCall(id="c2", name="echo", arguments={"message": "x"}),
    )
    assert tool_calls_from_chat(None, error=_Err) == ()
    assert (
        tool_calls_from_chat([{"id": "c", "function": {"name": "e", "arguments": ""}}], error=_Err)[
            0
        ].arguments
        == {}
    )


@pytest.mark.parametrize(
    "raw",
    [
        "nope",
        [{"function": {"name": "e", "arguments": "{}"}}],
        [{"id": "c", "function": {"arguments": "{}"}}],
        [{"id": "c", "function": {"name": "e", "arguments": "not json"}}],
        [{"id": "c", "function": {"name": "e", "arguments": "[1]"}}],
        [{"id": "c", "function": {"name": "e", "arguments": 5}}],
    ],
)
def test_malformed_tool_calls_raise_the_given_error(raw: object) -> None:
    with pytest.raises(_Err):
        tool_calls_from_chat(raw, error=_Err)
