"""Integration test: the Sprint 7 permission gap, closed.

`tests/test_execution_integration.py` proved Execution Core end-to-end for
permission-free tools. `HealthCheckTool` requires `KERNEL_INTERNAL`, and
Sprint 7's review documented that no permissioned tool could be driven
through `ExecutionEngine` -- `Dispatcher` never had a way to forward
granted permissions. This test proves that gap is now closed, built
entirely from a real bootstrapped runtime.
"""

from __future__ import annotations

from mellivor_kernel.authorization import AuthorizationEngine, PermissionResolver
from mellivor_kernel.bootstrap import BootstrapBuilder, RuntimeContext
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget


def _make_authorized_engine() -> tuple[ExecutionEngine, RuntimeContext]:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()
    dispatcher = Dispatcher(runtime.tool_registry, runtime.provider_registry)
    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry))
    engine = ExecutionEngine(dispatcher, authorizer=authorizer)
    return engine, runtime


def test_permissioned_tool_denied_without_the_required_permission() -> None:
    engine, runtime = _make_authorized_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check"),
        runtime.execution_context(),
    )

    assert result.success is False
    assert result.metadata["stage"] == "authorization"
    assert "kernel.internal" in (result.error or "")


def test_permissioned_tool_succeeds_once_the_permission_is_granted() -> None:
    engine, runtime = _make_authorized_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="health_check"),
        runtime.execution_context(),
        granted_permissions=frozenset({"kernel.internal"}),
    )

    assert result.success is True
    assert result.payload is not None
    assert result.payload["healthy"] is True


def test_permission_free_tool_unaffected_by_authorization() -> None:
    engine, runtime = _make_authorized_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1}),
        runtime.execution_context(),
    )

    assert result.success is True
    assert result.payload == {"x": 1}


def test_provider_target_is_unaffected_by_authorization() -> None:
    """Providers have no permission model in `BaseProvider`, so wiring
    authorization in must not block (or require anything for) the
    provider path -- it should fail (or succeed) exactly as it did before
    Sprint 8, on dispatch grounds only, never on authorization grounds.
    """
    engine, runtime = _make_authorized_engine()

    result = engine.execute(
        ExecutionRequest(target=ExecutionTarget.PROVIDER, operation="not-registered"),
        runtime.execution_context(),
    )

    assert result.success is False
    assert result.metadata.get("stage") != "authorization"
    assert result.metadata["target"] == "provider"
