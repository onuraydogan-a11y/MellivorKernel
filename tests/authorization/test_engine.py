"""Tests for mellivor_kernel.authorization.engine."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mellivor_kernel.authorization import (
    AuthorizationDenied,
    AuthorizationEngine,
    AuthorizationError,
    AuthorizationGranted,
    AuthorizationRequest,
    PermissionResolver,
    PermissionSet,
)
from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.events import Event, EventHandler, EventRegistration
from mellivor_kernel.execution import ExecutionContext, ExecutionRequest, ExecutionTarget
from mellivor_kernel.security import AuditRecord
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool, HealthCheckTool
from mellivor_kernel.tools.permissions import (
    KERNEL_INTERNAL,
    NETWORK_READ,
    PROVIDER_INVOKE,
    Permission,
)


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(HealthCheckTool())
    return registry


def _make_engine() -> AuthorizationEngine:
    return AuthorizationEngine(PermissionResolver(_make_registry()))


class _RecordingEventBus:
    """A minimal object satisfying `EventBus` structurally, deliberately not
    `InMemoryEventBus`.
    """

    def __init__(self) -> None:
        self.published: list[Event] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration:
        raise NotImplementedError

    def unsubscribe(self, registration: EventRegistration) -> None:
        raise NotImplementedError


class _RecordingAuditSink:
    """A minimal object satisfying `AuditSink` structurally, deliberately
    not a real sink implementation -- proving `AuthorizationEngine` only
    depends on the Protocol shape.
    """

    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, record: AuditRecord) -> None:
        self.recorded.append(record)


def _make_context() -> ExecutionContext:
    settings = _FakeSettings()
    return ExecutionContext(
        configuration=settings,
        logger=get_logger("test_authorization_engine"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


# -- authorize(): the pure decision, via AuthorizationRequest -----------------


def test_authorized_execution_with_exact_permissions() -> None:
    engine = _make_engine()
    request = AuthorizationRequest(
        target=ExecutionTarget.TOOL,
        operation="health_check",
        granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL})),
    )

    result = engine.authorize(request)

    assert result.granted is True
    assert result.granted_permissions.permissions == frozenset({KERNEL_INTERNAL})


def test_authorized_execution_with_superset_of_permissions() -> None:
    engine = _make_engine()
    request = AuthorizationRequest(
        target=ExecutionTarget.TOOL,
        operation="health_check",
        granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL, NETWORK_READ})),
    )

    result = engine.authorize(request)

    assert result.granted is True


def test_unauthorized_execution_with_no_permissions() -> None:
    engine = _make_engine()
    request = AuthorizationRequest(target=ExecutionTarget.TOOL, operation="health_check")

    result = engine.authorize(request)

    assert result.granted is False
    assert "kernel.internal" in (result.reason or "")


def test_missing_permissions_are_named_in_the_denial_reason() -> None:
    engine = _make_engine()
    request = AuthorizationRequest(
        target=ExecutionTarget.TOOL,
        operation="health_check",
        granted_permissions=PermissionSet(frozenset({NETWORK_READ})),
    )

    result = engine.authorize(request)

    assert result.granted is False
    assert "kernel.internal" in (result.reason or "")


def test_multiple_missing_permissions_are_all_named() -> None:
    class _MultiPermissionTool(EchoTool):
        @property
        def id(self) -> str:
            return "multi-permission"

        @property
        def permissions(self) -> frozenset[Permission]:
            return frozenset({KERNEL_INTERNAL, NETWORK_READ, PROVIDER_INVOKE})

    registry = ToolRegistry()
    registry.register(_MultiPermissionTool())
    engine = AuthorizationEngine(PermissionResolver(registry))
    request = AuthorizationRequest(target=ExecutionTarget.TOOL, operation="multi-permission")

    result = engine.authorize(request)

    assert result.granted is False
    assert "kernel.internal" in (result.reason or "")
    assert "network.read" in (result.reason or "")
    assert "provider.invoke" in (result.reason or "")


def test_empty_permission_set_authorizes_a_permission_free_tool() -> None:
    engine = _make_engine()
    request = AuthorizationRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.authorize(request)

    assert result.granted is True
    assert result.granted_permissions == PermissionSet.empty()


def test_provider_authorization_path_is_always_granted() -> None:
    """Provider target: BaseProvider has no permission model, so
    authorization never blocks it, regardless of claimed permissions.
    """
    engine = _make_engine()
    request = AuthorizationRequest(target=ExecutionTarget.PROVIDER, operation="anything")

    result = engine.authorize(request)

    assert result.granted is True


def test_tool_authorization_path_enforces_declared_permissions() -> None:
    engine = _make_engine()

    denied = engine.authorize(
        AuthorizationRequest(target=ExecutionTarget.TOOL, operation="health_check")
    )
    granted = engine.authorize(
        AuthorizationRequest(
            target=ExecutionTarget.TOOL,
            operation="health_check",
            granted_permissions=PermissionSet(frozenset({KERNEL_INTERNAL})),
        )
    )

    assert denied.granted is False
    assert granted.granted is True


# -- check(): the ExecutionEngine-facing adapter ------------------------------


def test_check_authorizes_an_execution_request() -> None:
    engine = _make_engine()
    context = _make_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    result = engine.check(request, context, granted_permissions=frozenset({"kernel.internal"}))

    assert result.granted is True


def test_check_denies_an_execution_request_missing_permissions() -> None:
    engine = _make_engine()
    context = _make_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    result = engine.check(request, context, granted_permissions=frozenset())

    assert result.granted is False


def test_check_denies_cleanly_on_malformed_permission_string() -> None:
    engine = _make_engine()
    context = _make_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.check(request, context, granted_permissions=frozenset({"NOT VALID"}))

    assert result.granted is False
    assert result.reason is not None


@pytest.mark.parametrize("blank", ["", "   "])
def test_invalid_authorization_request_rejected(blank: str) -> None:
    with pytest.raises(AuthorizationError):
        AuthorizationRequest(target=ExecutionTarget.TOOL, operation=blank)


# -- event publication --------------------------------------------------------


def test_authorize_never_publishes_events() -> None:
    """`authorize()` is a pure decision function -- event publication is
    `check()`'s responsibility only, since only it has a request id to
    correlate events with.
    """
    event_bus = _RecordingEventBus()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), event_bus=event_bus)

    engine.authorize(AuthorizationRequest(target=ExecutionTarget.TOOL, operation="echo"))

    assert event_bus.published == []


def test_check_publishes_authorization_granted_on_success() -> None:
    event_bus = _RecordingEventBus()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), event_bus=event_bus)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    engine.check(request, _make_context(), granted_permissions=frozenset({"kernel.internal"}))

    assert len(event_bus.published) == 1
    event = event_bus.published[0]
    assert isinstance(event, AuthorizationGranted)
    assert event.request_id == request.request_id
    assert event.granted_permissions == frozenset({"kernel.internal"})


def test_check_publishes_authorization_denied_on_missing_permissions() -> None:
    event_bus = _RecordingEventBus()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), event_bus=event_bus)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    engine.check(request, _make_context(), granted_permissions=frozenset())

    assert len(event_bus.published) == 1
    event = event_bus.published[0]
    assert isinstance(event, AuthorizationDenied)
    assert event.request_id == request.request_id
    assert "kernel.internal" in event.reason


def test_check_publishes_authorization_denied_on_malformed_permission() -> None:
    event_bus = _RecordingEventBus()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), event_bus=event_bus)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine.check(request, _make_context(), granted_permissions=frozenset({"NOT VALID"}))

    assert len(event_bus.published) == 1
    assert isinstance(event_bus.published[0], AuthorizationDenied)


def test_check_without_an_event_bus_publishes_nothing() -> None:
    engine = _make_engine()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.check(request, _make_context(), granted_permissions=frozenset())

    assert result.granted is True  # no event bus wired in, nothing to assert on it


# -- audit recording -----------------------------------------------------------


def test_authorize_never_records_audit() -> None:
    """`authorize()` is a pure decision function -- audit recording is
    `check()`'s responsibility only, matching event publication.
    """
    audit_sink = _RecordingAuditSink()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), audit_sink=audit_sink)

    engine.authorize(AuthorizationRequest(target=ExecutionTarget.TOOL, operation="echo"))

    assert audit_sink.recorded == []


def test_check_records_an_audit_entry_on_grant() -> None:
    audit_sink = _RecordingAuditSink()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), audit_sink=audit_sink)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    engine.check(request, _make_context(), granted_permissions=frozenset({"kernel.internal"}))

    assert len(audit_sink.recorded) == 1
    record = audit_sink.recorded[0]
    assert record.event == "authorization.granted"
    assert record.subject == request.request_id
    assert record.action == "tool:health_check"
    assert record.decision.allowed is True


def test_check_records_an_audit_entry_on_denial_for_missing_permissions() -> None:
    audit_sink = _RecordingAuditSink()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), audit_sink=audit_sink)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    engine.check(request, _make_context(), granted_permissions=frozenset())

    assert len(audit_sink.recorded) == 1
    record = audit_sink.recorded[0]
    assert record.event == "authorization.denied"
    assert record.decision.allowed is False
    assert "kernel.internal" in record.decision.reason


def test_check_records_an_audit_entry_on_malformed_permission() -> None:
    audit_sink = _RecordingAuditSink()
    engine = AuthorizationEngine(PermissionResolver(_make_registry()), audit_sink=audit_sink)
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    engine.check(request, _make_context(), granted_permissions=frozenset({"NOT VALID"}))

    assert len(audit_sink.recorded) == 1
    assert audit_sink.recorded[0].event == "authorization.denied"
    assert audit_sink.recorded[0].decision.allowed is False


def test_check_without_an_audit_sink_records_nothing() -> None:
    """No audit sink configured: identical to this engine's pre-Sprint-17
    behavior -- no recording, no error.
    """
    engine = _make_engine()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.check(request, _make_context(), granted_permissions=frozenset())

    assert result.granted is True  # no audit sink wired in, nothing to assert on it


def test_check_publishes_events_and_records_audit_identically() -> None:
    """Proves both mechanisms observe the same grant/deny decision for the
    same request, wired side by side with no interaction between them.
    """
    event_bus = _RecordingEventBus()
    audit_sink = _RecordingAuditSink()
    engine = AuthorizationEngine(
        PermissionResolver(_make_registry()), event_bus=event_bus, audit_sink=audit_sink
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    engine.check(request, _make_context(), granted_permissions=frozenset({"kernel.internal"}))

    assert len(event_bus.published) == len(audit_sink.recorded) == 1
    assert isinstance(event_bus.published[0], AuthorizationGranted)
    assert audit_sink.recorded[0].event == "authorization.granted"
    assert event_bus.published[0].request_id == audit_sink.recorded[0].subject == request.request_id
