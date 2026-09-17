"""Tests for mellivor_kernel.providers.tool_calling."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.providers import (
    ProviderError,
    ToolCall,
    ToolCallingError,
    ToolResultBlock,
    ToolSpec,
)


def test_tool_spec_defaults_to_empty_object_schema() -> None:
    spec = ToolSpec(name="echo", description="Echo the input.")

    assert spec.input_schema == {"type": "object"}


def test_tool_spec_freezes_input_schema() -> None:
    schema: dict[str, object] = {"type": "object", "properties": {"text": {"type": "string"}}}
    spec = ToolSpec(name="echo", description="Echo.", input_schema=schema)

    schema["properties"] = {}

    assert spec.input_schema["properties"] == {"text": {"type": "string"}}
    with pytest.raises(TypeError):
        spec.input_schema["type"] = "array"  # type: ignore[index]


@pytest.mark.parametrize(
    ("name", "description", "schema"),
    [
        ("", "desc", {"type": "object"}),
        ("  ", "desc", {"type": "object"}),
        ("echo", "", {"type": "object"}),
        ("echo", "desc", {"type": "array"}),
        ("echo", "desc", {}),
    ],
)
def test_tool_spec_rejects_malformed_values(
    name: str, description: str, schema: dict[str, object]
) -> None:
    with pytest.raises(ToolCallingError):
        ToolSpec(name=name, description=description, input_schema=schema)


def test_tool_call_freezes_arguments_and_defaults_to_empty() -> None:
    arguments: dict[str, object] = {"text": "hi"}
    call = ToolCall(id="call_1", name="echo", arguments=arguments)
    arguments["text"] = "changed"

    assert call.arguments == {"text": "hi"}
    assert ToolCall(id="call_2", name="echo").arguments == {}


@pytest.mark.parametrize(("call_id", "name"), [("", "echo"), ("call_1", ""), (" ", " ")])
def test_tool_call_rejects_blank_identity(call_id: str, name: str) -> None:
    with pytest.raises(ToolCallingError):
        ToolCall(id=call_id, name=name)


def test_tool_result_block_defaults_to_success() -> None:
    block = ToolResultBlock(tool_call_id="call_1", content="ok")

    assert block.is_error is False


def test_tool_result_block_rejects_blank_id() -> None:
    with pytest.raises(ToolCallingError):
        ToolResultBlock(tool_call_id="", content="ok")


def test_values_are_immutable() -> None:
    spec = ToolSpec(name="echo", description="Echo.")
    call = ToolCall(id="c", name="echo")
    block = ToolResultBlock(tool_call_id="c", content="ok")

    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.name = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        call.name = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        block.content = "x"  # type: ignore[misc]


def test_tool_calling_error_is_a_provider_error() -> None:
    assert issubclass(ToolCallingError, ProviderError)
