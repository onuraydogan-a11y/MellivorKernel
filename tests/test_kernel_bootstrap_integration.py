"""End-to-end test: load_config -> BootstrapBuilder -> RuntimeContext ->
running a registered tool through the pipeline.
"""

from __future__ import annotations

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import Environment, load_config
from mellivor_kernel.core import KernelState
from mellivor_kernel.providers import ProviderRegistry
from mellivor_kernel.tools import ToolExecutionPipeline


def test_kernel_boots_end_to_end_from_environment_variables() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test", "MELLIVOR_LOG_LEVEL": "DEBUG"})
    assert config.environment == Environment.TEST

    context = BootstrapBuilder(config).with_builtin_tools().build()

    assert context.state == KernelState.RUNNING
    assert context.health().healthy is True

    version_tool = context.tool_registry.lookup("version")
    result = ToolExecutionPipeline().run(version_tool, context.tool_context(), {})

    assert result.success is True
    assert result.payload is not None
    assert "version" in result.payload

    assert context.services.resolve(ProviderRegistry) is context.provider_registry
