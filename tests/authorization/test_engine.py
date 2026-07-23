"""Tests for mellivor_kernel.authorization.engine."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mellivor_kernel.authorization import (
    AuthorizationEngine,
    AuthorizationError,
    AuthorizationRequest,
    PermissionResolver,
    PermissionSet,
)
from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import ExecutionContext, ExecutionRequest, ExecutionTarget
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
