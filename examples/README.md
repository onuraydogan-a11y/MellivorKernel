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
- [`execution_with_authorization.py`](execution_with_authorization.py) —
  the same Tool Invocation path with an `AuthorizationEngine` wired in:
  a permissioned tool (`HealthCheckTool`) is denied without the right
  permissions and succeeds once granted, proving the gap
  `execution_tool_invocation.py`'s permission-free `echo` tool doesn't
  exercise.
- [`execution_with_events.py`](execution_with_events.py) — the same
  denied-then-granted flow with an `InMemoryEventBus` wired into both
  `ExecutionEngine` and `AuthorizationEngine`: a single handler subscribes
  to every event type and prints the full lifecycle sequence, correlated
  by `request_id`, for both outcomes.

Run any of them with `python examples/<name>.py` from the repository root.
