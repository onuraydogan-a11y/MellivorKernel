"""Tests for mellivor_kernel.bootstrap.builder.BootstrapBuilder."""

from __future__ import annotations

import pytest

from mellivor_kernel.bootstrap import BootstrapBuilder, BootstrapError
from mellivor_kernel.config import KernelConfig
from mellivor_kernel.core import KernelState, ServiceContainer
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry


def test_build_with_no_overrides_starts_the_kernel() -> None:
    context = BootstrapBuilder(KernelConfig()).build()

    assert context.state == KernelState.RUNNING


def test_with_container_overrides_the_default() -> None:
    container = ServiceContainer()

    context = BootstrapBuilder(KernelConfig()).with_container(container).build()

    assert context.services is container


def test_with_provider_registry_overrides_the_default() -> None:
    provider_registry = ProviderRegistry()

    context = BootstrapBuilder(KernelConfig()).with_provider_registry(provider_registry).build()

    assert context.provider_registry is provider_registry


def test_with_tool_registry_overrides_the_default() -> None:
    tool_registry = ToolRegistry()

    context = BootstrapBuilder(KernelConfig()).with_tool_registry(tool_registry).build()

    assert context.tool_registry is tool_registry


def test_with_service_registers_an_extra_service() -> None:
    class _Marker:
        pass

    marker = _Marker()

    context = BootstrapBuilder(KernelConfig()).with_service(_Marker, marker).build()

    assert context.services.resolve(_Marker) is marker


def test_with_builtin_tools_registers_the_demonstration_tools() -> None:
    context = BootstrapBuilder(KernelConfig()).with_builtin_tools().build()

    ids = {metadata.id for metadata in context.tool_registry.enumerate()}
    assert ids == {"echo", "health_check", "version"}


def test_without_with_builtin_tools_the_registry_stays_empty() -> None:
    context = BootstrapBuilder(KernelConfig()).build()

    assert context.tool_registry.enumerate() == ()


def test_builder_methods_are_chainable() -> None:
    builder = BootstrapBuilder(KernelConfig())

    result = builder.with_container(ServiceContainer()).with_builtin_tools()

    assert result is builder


def test_build_failure_is_wrapped_as_bootstrap_error() -> None:
    container = ServiceContainer()
    container.register_instance(KernelConfig, KernelConfig())

    with pytest.raises(BootstrapError):
        BootstrapBuilder(KernelConfig()).with_container(container).build()
