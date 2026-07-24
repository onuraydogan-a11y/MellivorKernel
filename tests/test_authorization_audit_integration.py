"""Integration test: AuthorizationEngine recording to security.AuditSink and
publishing to events.EventBus side by side, wired through a bootstrapped
runtime and a real ExecutionEngine.

Sprint 17 (Foundation Adoption): proves the security foundation (ADR-0012)
is consumable by a real subsystem, not just its own foundation tests --
built entirely from already-public bootstrap output, with no change to
`bootstrap`, `tools`, or `providers`.
"""

from __future__ import annotations

from mellivor_kernel.authorization import (
    AuthorizationDenied,
    AuthorizationEngine,
    AuthorizationGranted,
    PermissionResolver,
)
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.events import Event, InMemoryEventBus
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget
from mellivor_kernel.security import AuditRecord


class _EventRecorder:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


class _AuditRecorder:
    def __init__(self) -> None:
        self.recorded: list[AuditRecord] = []

    def record(self, record: AuditRecord) -> None:
        self.recorded.append(record)


def test_authorization_denial_is_audited_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    recorder = _EventRecorder()
    bus.subscribe(AuthorizationDenied, recorder)
    audit_sink = _AuditRecorder()

    authorizer = AuthorizationEngine(
        PermissionResolver(runtime.tool_registry), event_bus=bus, audit_sink=audit_sink
    )
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), authorizer=authorizer
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    result = engine.execute(request, runtime.execution_context())

    assert result.success is False
    assert len(recorder.events) == 1
    assert len(audit_sink.recorded) == 1

    denied_event = recorder.events[0]
    audit_record = audit_sink.recorded[0]
    assert isinstance(denied_event, AuthorizationDenied)
    assert audit_record.event == "authorization.denied"
    assert audit_record.decision.allowed is False
    assert denied_event.request_id == audit_record.subject == request.request_id


def test_authorization_grant_is_audited_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    recorder = _EventRecorder()
    bus.subscribe(AuthorizationGranted, recorder)
    audit_sink = _AuditRecorder()

    authorizer = AuthorizationEngine(
        PermissionResolver(runtime.tool_registry), event_bus=bus, audit_sink=audit_sink
    )
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), authorizer=authorizer
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    result = engine.execute(
        request, runtime.execution_context(), granted_permissions=frozenset({"kernel.internal"})
    )

    assert result.success is True
    assert len(recorder.events) == 1
    assert len(audit_sink.recorded) == 1

    granted_event = recorder.events[0]
    audit_record = audit_sink.recorded[0]
    assert isinstance(granted_event, AuthorizationGranted)
    assert audit_record.event == "authorization.granted"
    assert audit_record.decision.allowed is True
    assert granted_event.request_id == audit_record.subject == request.request_id


def test_authorization_with_only_audit_sink_configured_leaves_event_bus_untouched() -> None:
    """Configuring `audit_sink` alone must not change `EventBus`
    behavior -- the two mechanisms are independent, not coupled.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    audit_sink = _AuditRecorder()
    authorizer = AuthorizationEngine(
        PermissionResolver(runtime.tool_registry), audit_sink=audit_sink
    )
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), authorizer=authorizer
    )
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo")

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert len(audit_sink.recorded) == 1
    assert audit_sink.recorded[0].event == "authorization.granted"
