# examples

Minimal, runnable examples showing how a product consumes the kernel. Added
once there is a kernel to consume — kept intentionally out of `src/` so
examples never become a dependency of the kernel itself.

- [`execution_tool_invocation.py`](execution_tool_invocation.py) — the Tool
  Invocation path through Execution Core:
  `ExecutionRequest` → `ExecutionEngine` → `Dispatcher` → Tool Runtime →
  `ExecutionResult`.
- [`execution_provider_invocation.py`](execution_provider_invocation.py) —
  the equivalent Provider Invocation path, against a test-only provider
  (not a production integration).

Run either with `python examples/<name>.py` from the repository root.
