"""Tests for mellivor_kernel.tools.metadata."""

from __future__ import annotations

from mellivor_kernel.tools import NETWORK_READ, ToolMetadata


def test_metadata_holds_declared_fields() -> None:
    metadata = ToolMetadata(
        id="echo",
        name="Echo Tool",
        version="1.0.0",
        description="Echoes back the request.",
        capabilities=frozenset({"diagnostic"}),
        permissions=frozenset({NETWORK_READ}),
    )

    assert metadata.id == "echo"
    assert metadata.name == "Echo Tool"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Echoes back the request."
    assert metadata.capabilities == frozenset({"diagnostic"})
    assert metadata.permissions == frozenset({NETWORK_READ})
