"""End-to-end test wiring ToolRegistry and ToolExecutionPipeline together."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.tools import ToolContext, ToolExecutionPipeline, ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool, HealthCheckTool, VersionTool
from mellivor_kernel.tools.permissions import KERNEL_INTERNAL


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


def test_registered_builtin_tools_run_through_the_pipeline() -> None:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    kernel.start()
    context = ToolContext(
        configuration=settings,
        logger=get_logger("test_tool_bootstrap"),
        runtime=kernel,
        services=ServiceContainer(),
    )

    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(HealthCheckTool())
    registry.register(VersionTool())

    pipeline = ToolExecutionPipeline()

    echo_result = pipeline.run(registry.lookup("echo"), context, {"ping": "pong"})
    assert echo_result.success is True
    assert echo_result.payload == {"ping": "pong"}

    version_result = pipeline.run(registry.lookup("version"), context, {})
    assert version_result.success is True

    health_result = pipeline.run(
        registry.lookup("health_check"),
        context,
        {},
        granted_permissions=frozenset({KERNEL_INTERNAL}),
    )
    assert health_result.success is True
    assert health_result.payload is not None
    assert health_result.payload["healthy"] is True

    assert {metadata.id for metadata in registry.enumerate()} == {
        "echo",
        "health_check",
        "version",
    }
