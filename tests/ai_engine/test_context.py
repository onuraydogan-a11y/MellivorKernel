"""Tests for mellivor_kernel.ai_engine.context."""

from __future__ import annotations

import dataclasses

import pytest

from mellivor_kernel.agents import AgentContext
from mellivor_kernel.ai_engine.context import AIEngineContext
from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.execution import ExecutionContext
from mellivor_kernel.plugins import PluginContext
from mellivor_kernel.workflow import WorkflowContext


class _FakeSettings:
    log_level = "INFO"


def _make_context() -> AIEngineContext:
    settings = _FakeSettings()
    return AIEngineContext(
        configuration=settings,
        logger=get_logger("test_ai_engine_context"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_context_holds_all_four_fields() -> None:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    logger = get_logger("test_ai_engine_context_fields")
    services = ServiceContainer()

    context = AIEngineContext(
        configuration=settings, logger=logger, runtime=kernel, services=services
    )

    assert context.configuration is settings
    assert context.logger is logger
    assert context.runtime is kernel
    assert context.services is services


def test_context_is_immutable() -> None:
    context = _make_context()

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.services = ServiceContainer()  # type: ignore[misc]


def test_to_execution_context_uses_shared_fields() -> None:
    context = _make_context()

    execution_context = context.to_execution_context()

    assert isinstance(execution_context, ExecutionContext)
    assert execution_context.configuration is context.configuration
    assert execution_context.runtime is context.runtime
    assert execution_context.services is context.services
    assert execution_context.logger is context.logger


def test_to_execution_context_accepts_a_logger_override() -> None:
    context = _make_context()
    override = get_logger("override")

    execution_context = context.to_execution_context(logger=override)

    assert execution_context.logger is override


def test_to_workflow_context_wraps_a_fresh_execution_context() -> None:
    context = _make_context()

    workflow_context = context.to_workflow_context()

    assert isinstance(workflow_context, WorkflowContext)
    assert workflow_context.execution_context.runtime is context.runtime
    assert workflow_context.step_results == {}


def test_to_agent_context_wraps_a_fresh_workflow_context() -> None:
    context = _make_context()

    agent_context = context.to_agent_context()

    assert isinstance(agent_context, AgentContext)
    assert agent_context.workflow_context.execution_context.runtime is context.runtime


def test_to_plugin_context_uses_shared_fields() -> None:
    context = _make_context()

    plugin_context = context.to_plugin_context()

    assert isinstance(plugin_context, PluginContext)
    assert plugin_context.configuration is context.configuration
    assert plugin_context.runtime is context.runtime
    assert plugin_context.services is context.services
