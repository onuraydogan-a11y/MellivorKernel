"""End-to-end example: the Sprint 7 permission gap, closed.

`HealthCheckTool` requires the `kernel.internal` permission. Sprint 7's
integration gate documented that no permissioned tool could be driven
through `ExecutionEngine` -- `Dispatcher` had no way to forward granted
permissions. This example proves the fix: the same request is denied
without an `AuthorizationEngine` wired in (or with the wrong permissions),
and succeeds once wired in with the right ones.

Run directly: `python examples/execution_with_authorization.py`
"""

from __future__ import annotations

from mellivor_kernel.authorization import AuthorizationEngine, PermissionResolver
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "WARNING"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    dispatcher = Dispatcher(runtime.tool_registry, runtime.provider_registry)
    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry))
    engine = ExecutionEngine(dispatcher, authorizer=authorizer)
    context = runtime.execution_context()
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check")

    denied = engine.execute(request, context)
    print(f"without permissions: success={denied.success} error={denied.error!r}")
    assert denied.success is False
    assert denied.metadata["stage"] == "authorization"

    granted = engine.execute(request, context, granted_permissions=frozenset({"kernel.internal"}))
    print(f"with kernel.internal:  success={granted.success} payload={granted.payload}")
    assert granted.success is True


if __name__ == "__main__":
    main()
