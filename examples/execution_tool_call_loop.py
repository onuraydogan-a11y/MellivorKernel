"""Model-driven tool selection through `ToolCallLoop` (ADR-0028).

A scripted, test-only provider stands in for a real model so the example
runs offline: on the first turn it "decides" to call the `echo` tool, on
the second it answers in text. Every tool call goes through
`ExecutionEngine`, so swapping in an authorizer, memory store or event bus
works exactly as in the other execution examples.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionEngine,
    ToolCallLoop,
    ToolLoopOptions,
)
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
    ToolCall,
)


class ScriptedProvider(BaseProvider):
    """Test-only: not a production integration."""

    def __init__(self, configuration: ProviderConfiguration) -> None:
        super().__init__(configuration)
        self._turn = 0

    @property
    def name(self) -> str:
        return "scripted"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_tool_calls=True)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self._turn += 1
        tools = request.get("tools", ())
        offered = [spec.name for spec in tools] if isinstance(tools, Sequence) else []
        if self._turn == 1:
            return {
                "text": f"I can use {offered}; calling echo.",
                "tool_calls": (ToolCall(id="call_1", name="echo", arguments={"message": "ping"}),),
            }
        messages = request["messages"]
        assert isinstance(messages, Sequence)
        last = messages[-1]
        assert isinstance(last, Mapping)
        blocks = last["content"]
        assert isinstance(blocks, Sequence) and isinstance(blocks[0], Mapping)
        return {"text": f"The tool returned: {blocks[0]['content']}", "tool_calls": ()}


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "INFO"})
    providers = ProviderRegistry()
    providers.register(ScriptedProvider(ProviderConfiguration(provider_name="scripted")))
    runtime = (
        BootstrapBuilder(config).with_builtin_tools().with_provider_registry(providers).build()
    )

    engine = ExecutionEngine(Dispatcher(runtime.tool_registry, runtime.provider_registry))
    loop = ToolCallLoop(engine, runtime.tool_registry, runtime.provider_registry)

    result = loop.run(
        "scripted",
        [{"role": "user", "content": "echo ping for me"}],
        ["echo"],
        runtime.execution_context(),
        options=ToolLoopOptions(max_iterations=4),
    )

    print(f"success={result.success} iterations={result.iterations}")
    for record in result.tool_calls:
        print(f"tool={record.call.name} executed={record.executed} result={record.result}")
    print(f"answer={result.text}")

    assert result.success is True
    assert result.tool_calls[0].success is True
    assert result.text is not None and "ping" in result.text


if __name__ == "__main__":
    main()
