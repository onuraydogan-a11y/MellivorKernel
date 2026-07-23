"""End-to-end example: ExecutionRequest -> ExecutionEngine -> Dispatcher ->
Tool Runtime -> ExecutionResult.

Demonstrates the Tool Invocation path through Execution Core using only
already-public kernel APIs: `BootstrapBuilder` produces a running
`RuntimeContext`, which is enough to build both the `Dispatcher` and the
`ExecutionContext` an `ExecutionEngine` needs -- no internals reached into.

Run directly: `python examples/execution_tool_invocation.py`
"""

from __future__ import annotations

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import Environment, load_config
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "INFO"})
    assert config.environment == Environment.DEVELOPMENT

    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    dispatcher = Dispatcher(runtime.tool_registry, runtime.provider_registry)
    engine = ExecutionEngine(dispatcher)

    request = ExecutionRequest(
        target=ExecutionTarget.TOOL,
        operation="echo",
        payload={"message": "hello from Execution Core"},
    )

    result = engine.execute(request, runtime.execution_context())

    print(f"success={result.success}")
    print(f"payload={result.payload}")
    print(f"execution_time_seconds={result.execution_time_seconds:.6f}")
    print(f"metadata={dict(result.metadata)}")

    assert result.success is True
    assert result.payload == {"message": "hello from Execution Core"}


if __name__ == "__main__":
    main()
