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
- [`plugin_system_info.py`](plugin_system_info.py) — the `SystemInfoPlugin`
  built-in plugin (Sprint 20) driven through the complete Plugin SDK +
  Plugin Runtime path: `PluginBuilder` builds a manifest, `PluginLoader`
  validates and instantiates it, `PluginRegistry` registers it, and
  `PluginLifecycle` drives it through initialize/start/stop/dispose,
  printing the read-only kernel information it reports.
- [`plugin_discovery.py`](plugin_discovery.py) — Plugin Discovery
  (Sprint 21): discovers the `system-info` sample plugin from
  [`sample_plugins/`](sample_plugins/) -- a real filesystem location
  containing a manifest file, not a hand-constructed `PluginManifest` --
  loads and registers it through the unmodified `PluginLoader`/
  `PluginRegistry`, and drives it through the same lifecycle
  `plugin_system_info.py` demonstrates by hand.
- [`ai_engine_foundation.py`](ai_engine_foundation.py) — the AI Engine
  Foundation (Sprint 22): assembles a bootstrapped `RuntimeContext` into
  the full orchestration chain (`ExecutionEngine` -> `WorkflowEngine` ->
  `AgentEngine`, with an `AuthorizationEngine` consulted and an
  `InMemoryEventBus`/`InMemoryStore` attached) through `AIEngineBuilder`
  alone -- no engine constructed by hand, unlike every example above --
  then discovers and runs the `system-info` sample plugin through
  `with_plugin_discovery()`.

Run any of them with `python examples/<name>.py` from the repository root.
