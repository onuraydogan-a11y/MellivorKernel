"""Integration tests: ExecutionEngine recording to Memory, wired through a
bootstrapped runtime.

Proves Memory is usable as kernel infrastructure end-to-end -- built
entirely from already-public bootstrap output, with no change to
`bootstrap`, `tools`, or `providers`.
"""

from __future__ import annotations

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget
from mellivor_kernel.memory import Memory, MemoryQuery


def test_execution_records_to_memory_end_to_end() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    memory = Memory()
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), memory=memory
    )
    context = runtime.execution_context()

    echo_request = ExecutionRequest(
        target=ExecutionTarget.TOOL, operation="echo", payload={"greeting": "hi"}
    )
    version_request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="version")

    echo_result = engine.execute(echo_request, context)
    version_result = engine.execute(version_request, context)

    assert echo_result.success is True
    assert version_result.success is True

    echo_entry = memory.get(echo_request.request_id)
    assert echo_entry is not None
    assert echo_entry.metadata["operation"] == "echo"

    version_entry = memory.get(version_request.request_id)
    assert version_entry is not None
    assert version_entry.metadata["operation"] == "version"

    # Both recorded under the "tool" tag, searchable together.
    all_tool_memories = memory.search(MemoryQuery(tag="tool"))
    assert {entry.id for entry in all_tool_memories} == {
        echo_request.request_id,
        version_request.request_id,
    }


def test_execution_without_memory_configured_behaves_exactly_as_before() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    request = ExecutionRequest(target=ExecutionTarget.TOOL, operation="echo", payload={"x": 1})

    result = engine.execute(request, runtime.execution_context())

    assert result.success is True
    assert result.payload == {"x": 1}
