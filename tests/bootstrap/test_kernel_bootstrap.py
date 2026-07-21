"""Tests for mellivor_kernel.bootstrap.bootstrap.KernelBootstrap."""

from __future__ import annotations

import pytest

from mellivor_kernel.bootstrap import BootstrapError, KernelBootstrap
from mellivor_kernel.config import Environment, KernelConfig
from mellivor_kernel.core import KernelState, ServiceContainer, ServiceRegistrationError
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolRegistry


def test_run_starts_the_kernel() -> None:
    context = KernelBootstrap.run(KernelConfig())

    assert context.state == KernelState.RUNNING
    assert context.health().healthy is True


def test_run_registers_default_services() -> None:
    config = KernelConfig(environment=Environment.TEST)

    context = KernelBootstrap.run(config)

    assert context.services.resolve(KernelConfig) is config
    assert context.services.resolve(ProviderRegistry) is context.provider_registry
    assert context.services.resolve(ToolRegistry) is context.tool_registry


def test_run_creates_default_container_provider_registry_and_tool_registry() -> None:
    context = KernelBootstrap.run(KernelConfig())

    assert isinstance(context.services, ServiceContainer)
    assert isinstance(context.provider_registry, ProviderRegistry)
    assert isinstance(context.tool_registry, ToolRegistry)


def test_run_uses_supplied_container_provider_registry_and_tool_registry() -> None:
    container = ServiceContainer()
    provider_registry = ProviderRegistry()
    tool_registry = ToolRegistry()

    context = KernelBootstrap.run(
        KernelConfig(),
        container=container,
        provider_registry=provider_registry,
        tool_registry=tool_registry,
    )

    assert context.services is container
    assert context.provider_registry is provider_registry
    assert context.tool_registry is tool_registry


def test_run_registers_extra_services() -> None:
    class _Marker:
        pass

    marker = _Marker()

    context = KernelBootstrap.run(KernelConfig(), extra_services={_Marker: marker})

    assert context.services.resolve(_Marker) is marker


def test_run_can_register_builtin_tools() -> None:
    context = KernelBootstrap.run(KernelConfig(), register_builtin_tools=True)

    ids = {metadata.id for metadata in context.tool_registry.enumerate()}
    assert ids == {"echo", "health_check", "version"}


def test_run_does_not_register_builtin_tools_by_default() -> None:
    context = KernelBootstrap.run(KernelConfig())

    assert context.tool_registry.enumerate() == ()


def test_run_wraps_default_service_collision_as_bootstrap_error() -> None:
    container = ServiceContainer()
    container.register_instance(KernelConfig, KernelConfig())

    with pytest.raises(BootstrapError) as excinfo:
        KernelBootstrap.run(KernelConfig(), container=container)

    assert isinstance(excinfo.value.__cause__, ServiceRegistrationError)


def test_run_wraps_extra_service_collision_as_bootstrap_error() -> None:
    class _Marker:
        pass

    container = ServiceContainer()
    container.register_instance(_Marker, _Marker())

    with pytest.raises(BootstrapError) as excinfo:
        KernelBootstrap.run(
            KernelConfig(), container=container, extra_services={_Marker: _Marker()}
        )

    assert isinstance(excinfo.value.__cause__, ServiceRegistrationError)
