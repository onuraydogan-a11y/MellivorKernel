"""End-to-end example: ExecutionEngine and AuthorizationEngine publishing
lifecycle events to an InMemoryEventBus.

A single handler subscribes to every event type both engines publish and
prints them in order, showing the full sequence for a denied request
followed by a granted one -- ExecutionStarted -> AuthorizationDenied ->
ExecutionFailed, then ExecutionStarted -> AuthorizationGranted ->
ExecutionCompleted -- correlated by `request_id`.

Run directly: `python examples/execution_with_events.py`
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
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionCompleted,
    ExecutionEngine,
    ExecutionFailed,
    ExecutionRequest,
    ExecutionStarted,
    ExecutionTarget,
)


class PrintingHandler:
    """A handler satisfying `EventHandler` structurally: just prints."""

    def handle(self, event: Event) -> None:
        print(f"  [{type(event).__name__}] {event}")


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "WARNING"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    bus = InMemoryEventBus()
    handler = PrintingHandler()
    for event_type in (
        ExecutionStarted,
        ExecutionCompleted,
        ExecutionFailed,
        AuthorizationGranted,
        AuthorizationDenied,
    ):
        bus.subscribe(event_type, handler)

    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry), event_bus=bus)
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry),
        authorizer=authorizer,
        event_bus=bus,
    )
    context = runtime.execution_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    print("Without the required permission:")
    engine.execute(request, context)

    print("With the required permission:")
    engine.execute(request, context, granted_permissions=frozenset({"kernel.internal"}))


if __name__ == "__main__":
    main()
