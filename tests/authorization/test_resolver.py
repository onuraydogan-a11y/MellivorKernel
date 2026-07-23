"""Tests for mellivor_kernel.authorization.resolver."""

from __future__ import annotations

from mellivor_kernel.authorization import PermissionResolver, PermissionSet
from mellivor_kernel.execution import ExecutionTarget
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool, HealthCheckTool
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(HealthCheckTool())
    return registry


def test_resolves_a_permissioned_tools_requirements() -> None:
    resolver = PermissionResolver(_make_registry())

    required = resolver.resolve_required_permissions(ExecutionTarget.TOOL, "health_check")

    assert required.permissions == frozenset({KERNEL_INTERNAL})


def test_resolves_no_requirements_for_a_permission_free_tool() -> None:
    resolver = PermissionResolver(_make_registry())

    required = resolver.resolve_required_permissions(ExecutionTarget.TOOL, "echo")

    assert required == PermissionSet.empty()


def test_resolves_no_requirements_for_an_unregistered_tool() -> None:
    resolver = PermissionResolver(_make_registry())

    required = resolver.resolve_required_permissions(ExecutionTarget.TOOL, "does-not-exist")

    assert required == PermissionSet.empty()


def test_resolves_no_requirements_for_provider_target() -> None:
    resolver = PermissionResolver(_make_registry())

    required = resolver.resolve_required_permissions(ExecutionTarget.PROVIDER, "anything")

    assert required == PermissionSet.empty()
