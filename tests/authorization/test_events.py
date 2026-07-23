"""Tests for mellivor_kernel.authorization.events."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.authorization import AuthorizationDenied, AuthorizationGranted
from mellivor_kernel.events import Event
from mellivor_kernel.execution import ExecutionTarget


def test_authorization_granted_carries_identifying_fields() -> None:
    event = AuthorizationGranted(
        request_id="abc",
        target=ExecutionTarget.TOOL,
        operation="health_check",
        granted_permissions=frozenset({"kernel.internal"}),
    )

    assert isinstance(event, Event)
    assert event.request_id == "abc"
    assert event.target == ExecutionTarget.TOOL
    assert event.operation == "health_check"
    assert event.granted_permissions == frozenset({"kernel.internal"})


def test_authorization_granted_defaults_to_no_permissions() -> None:
    event = AuthorizationGranted(request_id="abc", target=ExecutionTarget.TOOL, operation="echo")

    assert event.granted_permissions == frozenset()


def test_authorization_denied_carries_reason() -> None:
    event = AuthorizationDenied(
        request_id="abc",
        target=ExecutionTarget.TOOL,
        operation="health_check",
        reason="Missing required permissions: kernel.internal.",
    )

    assert event.reason == "Missing required permissions: kernel.internal."


def test_authorization_events_are_immutable() -> None:
    event = AuthorizationDenied(
        request_id="abc", target=ExecutionTarget.TOOL, operation="echo", reason="denied"
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        event.reason = "other"  # type: ignore[misc]
