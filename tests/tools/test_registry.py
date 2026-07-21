"""Tests for mellivor_kernel.tools.registry."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from mellivor_kernel.tools import (
    BaseTool,
    ToolContext,
    ToolRegistrationError,
    ToolRegistry,
    ToolResult,
)
from mellivor_kernel.tools.permissions import Permission


class _FakeTool(BaseTool):
    def __init__(self, tool_id: str) -> None:
        self._id = tool_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._id

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A fake tool for registry tests."

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    @property
    def permissions(self) -> frozenset[Permission]:
        return frozenset()

    def validate(self, request: Mapping[str, object]) -> None:
        return

    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        return ToolResult(success=True, payload=dict(request))


def test_register_and_lookup() -> None:
    registry = ToolRegistry()
    tool = _FakeTool("alpha")

    registry.register(tool)

    assert registry.lookup("alpha") is tool


def test_register_twice_raises() -> None:
    registry = ToolRegistry()
    registry.register(_FakeTool("alpha"))

    with pytest.raises(ToolRegistrationError):
        registry.register(_FakeTool("alpha"))


def test_lookup_unregistered_raises() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolRegistrationError):
        registry.lookup("missing")


def test_unregister_removes_tool() -> None:
    registry = ToolRegistry()
    registry.register(_FakeTool("alpha"))

    registry.unregister("alpha")

    assert registry.exists("alpha") is False


def test_unregister_missing_raises() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolRegistrationError):
        registry.unregister("missing")


def test_exists() -> None:
    registry = ToolRegistry()
    assert registry.exists("alpha") is False

    registry.register(_FakeTool("alpha"))

    assert registry.exists("alpha") is True


def test_enumerate_returns_metadata_for_all_tools() -> None:
    registry = ToolRegistry()
    registry.register(_FakeTool("alpha"))
    registry.register(_FakeTool("beta"))

    ids = {metadata.id for metadata in registry.enumerate()}

    assert ids == {"alpha", "beta"}
