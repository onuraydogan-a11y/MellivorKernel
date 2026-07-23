"""End-to-end example: ExecutionRequest -> ExecutionEngine -> Dispatcher ->
Provider Runtime -> ExecutionResult.

Demonstrates the Provider Invocation path through Execution Core. The
provider used here (`EchoProvider`) is test-only: it satisfies the
`BaseProvider` contract but calls no external model or service, exactly
the way `tools.builtin.EchoTool` demonstrates the Tool Runtime without
calling anything external. It is not a production provider integration --
see `docs/adr/0003-repository-boundaries.md` on why one would never live
inside `mellivor_kernel.providers` itself.

Run directly: `python examples/execution_provider_invocation.py`
"""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionTarget,
)
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
)


class EchoProvider(BaseProvider):
    """A test-only provider that echoes its request back. Not for production use."""

    @property
    def name(self) -> str:
        return "echo-provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=False)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echoed": dict(request)}


def main() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "development", "MELLIVOR_LOG_LEVEL": "INFO"})

    provider_registry = ProviderRegistry()
    provider_registry.register(EchoProvider(ProviderConfiguration(provider_name="echo-provider")))

    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()

    dispatcher = Dispatcher(runtime.tool_registry, runtime.provider_registry)
    engine = ExecutionEngine(dispatcher)

    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER,
        operation="echo-provider",
        payload={"prompt": "hello from Execution Core"},
    )

    result = engine.execute(request, runtime.execution_context())

    print(f"success={result.success}")
    print(f"payload={result.payload}")
    print(f"execution_time_seconds={result.execution_time_seconds:.6f}")
    print(f"metadata={dict(result.metadata)}")

    assert result.success is True
    assert result.payload == {"echoed": {"prompt": "hello from Execution Core"}}


if __name__ == "__main__":
    main()
