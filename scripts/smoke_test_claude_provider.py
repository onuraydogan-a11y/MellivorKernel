"""Manual smoke test: a real Claude request through the complete kernel stack.

Not part of the automated test suite (lives outside `tests/`, which is the
only directory `pytest` collects from per `pyproject.toml`'s
`testpaths`) -- it makes a real network call to the Anthropic API and
costs real tokens, so it is never run in CI.

Requires:
    - `pip install mellivor-kernel[anthropic]`
    - the `ANTHROPIC_API_KEY` environment variable set to a real key

Usage:
    ANTHROPIC_API_KEY=sk-ant-... python scripts/smoke_test_claude_provider.py \
        [--model claude-haiku-4-5] [--prompt "Say hello in one word."]
"""

from __future__ import annotations

import argparse
import os
import sys

from mellivor_kernel.authorization import AuthorizationEngine, PermissionResolver
from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.execution import Dispatcher, ExecutionEngine, ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers import ProviderConfiguration, ProviderRegistry
from mellivor_kernel.providers.claude import ClaudeProviderError

try:
    from mellivor_kernel.providers.claude import ClaudeProvider
except ModuleNotFoundError:
    print(
        "The 'anthropic' package is not installed. Run: pip install mellivor-kernel[anthropic]",
        file=sys.stderr,
    )
    raise SystemExit(1) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--prompt", default="Say hello in exactly one word.")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 1

    config = load_config({"MELLIVOR_ENVIRONMENT": "development"})
    provider_registry = ProviderRegistry()
    provider_registry.register(
        ClaudeProvider(
            ProviderConfiguration(provider_name="claude", api_key=api_key, default_model=args.model)
        )
    )

    runtime = BootstrapBuilder(config).with_provider_registry(provider_registry).build()
    authorizer = AuthorizationEngine(PermissionResolver(runtime.tool_registry))
    engine = ExecutionEngine(
        Dispatcher(runtime.tool_registry, runtime.provider_registry), authorizer=authorizer
    )

    request = ExecutionRequest(
        target=ExecutionTarget.PROVIDER, operation="claude", payload={"prompt": args.prompt}
    )

    print(f"Sending prompt to {args.model}: {args.prompt!r}")
    result = engine.execute(request, runtime.execution_context())

    if not result.success:
        print(f"FAILED: {result.error}", file=sys.stderr)
        return 1

    payload = result.payload
    assert payload is not None
    print(f"Response: {payload['text']!r}")
    print(f"model={payload['model']} stop_reason={payload['stop_reason']}")
    print(f"input_tokens={payload['input_tokens']} output_tokens={payload['output_tokens']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClaudeProviderError as exc:
        print(f"Claude provider error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
