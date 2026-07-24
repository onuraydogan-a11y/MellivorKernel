# `ai_engine` subsystem spec

Status: Foundation (Sprint 22).

Public contract exported from `mellivor_kernel.ai_engine`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0018](../adr/0018-ai-engine-foundation.md) for why this sprint
exists and what it deliberately excludes (business logic, chat features,
prompting, reasoning, planning, orchestration decisions, provider
selection logic).

## Scope of this sprint

This spec defines a pure composition layer over an already-bootstrapped
`RuntimeContext` ([`bootstrap`](bootstrap.md)) and the orchestration-chain engines
(`ExecutionEngine` → `WorkflowEngine` → `AgentEngine`, with an
`Authorizer` optionally consulted, `mellivor_kernel.execution`/
`workflow`/`agents`/`authorization`) plus a `PluginRegistry`
(`mellivor_kernel.plugins`). It introduces no new decision logic:
`AIEngine.execute()`/`run_workflow()`/`run_agent()` call exactly
`ExecutionEngine.execute()`/`WorkflowEngine.run()`/`AgentEngine.execute()`,
with exactly the arguments given, and return exactly what that engine
returns.

## `AIEngineContext`

Internal only -- not exported from `mellivor_kernel.ai_engine`. No
supported code path ever hands one to a consumer (`AIEngine`'s own
context-builder methods return `ExecutionContext`/`WorkflowContext`/
`AgentContext`/`PluginContext`, never `AIEngineContext` itself), and it
is constructed only by `AIEngineBuilder`. Documented here because
`builder.py`/`engine.py` share it internally, not as a public contract.

```python
@dataclass(frozen=True, slots=True)
class AIEngineContext:
    configuration: KernelSettings
    logger: logging.Logger
    runtime: Kernel
    services: ServiceContainer

    def to_execution_context(self, *, logger: logging.Logger | None = None) -> ExecutionContext
    def to_workflow_context(self, *, logger: logging.Logger | None = None) -> WorkflowContext
    def to_agent_context(self, *, logger: logging.Logger | None = None) -> AgentContext
    def to_plugin_context(self, *, logger: logging.Logger | None = None) -> PluginContext
```

- Carries the same four fields every kernel-scoped context already
  carries (`ExecutionContext`, `WorkflowContext`'s wrapped
  `execution_context`, `PluginContext`) — introduces no new context
  shape.
- `to_workflow_context()` always wraps a **fresh** `to_execution_context()`
  call — `WorkflowContext.step_results` starts empty every time, matching
  `WorkflowContext`'s own default.
- `to_agent_context()` always wraps a **fresh** `to_workflow_context()`
  call, for the same reason.
- Each `to_*` method accepts an optional `logger` override; omitting it
  reuses `self.logger`.

## `AIEngine`

```python
class AIEngine:
    # Constructed only by AIEngineBuilder.build() -- never directly.

    @property
    def runtime(self) -> RuntimeContext: ...
    @property
    def plugin_registry(self) -> PluginRegistry: ...

    def execute(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult: ...
    def run_workflow(self, workflow: Workflow, context: WorkflowContext) -> WorkflowResult: ...
    def run_agent(self, agent: Agent, context: AgentContext) -> AgentResult: ...

    def execution_context(self, *, logger_name: str = "execution") -> ExecutionContext: ...
    def workflow_context(self, *, logger_name: str = "workflow") -> WorkflowContext: ...
    def agent_context(self, *, logger_name: str = "agents") -> AgentContext: ...
    def plugin_context(self, *, logger_name: str = "plugins") -> PluginContext: ...

    def start_plugins(self) -> None: ...
    def stop_plugins(self) -> None: ...
    def dispose_plugins(self) -> None: ...
```

- **Only `.runtime` and `.plugin_registry` are exposed** — never the
  composed `ExecutionEngine`/`WorkflowEngine`/`AgentEngine`/`Authorizer`
  themselves. Exposing those would let a caller permanently bypass
  `execute()`/`run_workflow()`/`run_agent()`, foreclosing any future
  ability to add engine-level behavior without a breaking change once
  external code depends on the direct path. `plugin_registry` is not a
  bypass of any `AIEngine` method — it is the object other code
  registers plugins into before calling `start_plugins()`.
- **Delegated operations** — `execute()`, `run_workflow()`,
  `run_agent()` each call exactly one existing engine method and return
  its result unmodified. `AIEngine` never inspects, retries, or
  transforms the result.
- **Context builders** — each of the four builds a fresh context from
  the `AIEngineContext` supplied at construction, with a logger obtained
  via `core.logging.get_logger(logger_name)`. Callers are not required to
  use these; any independently constructed `ExecutionContext`/
  `WorkflowContext`/`AgentContext` works identically with `execute()`/
  `run_workflow()`/`run_agent()`, since those methods only require the
  Protocol/dataclass shape the underlying engine already expects.
- **Plugin lifecycle** — the one lifecycle `AIEngine` owns, since the
  underlying `Kernel`'s own lifecycle already ran to completion inside
  `BootstrapBuilder.build()` before an `AIEngine` exists.
  - `start_plugins()` re-reads `plugin_registry.enumerate()` on every
    call — a plugin registered into the same `PluginRegistry` after this
    `AIEngine` was built is still picked up on the next call. For each
    plugin id, `AIEngine` holds one `PluginLifecycle` for its own
    lifetime (created lazily on first use). A plugin whose lifecycle is
    still `REGISTERED` is `initialize()`d then `start()`ed; a plugin
    already past `REGISTERED` (for example one this `AIEngine`
    previously `stop_plugins()`-ed) is only `start()`ed again —
    `PluginLifecycle.initialize()` only permits being called once, from
    `REGISTERED`.
  - `stop_plugins()`/`dispose_plugins()` call `PluginLifecycle.stop()`/
    `.dispose()` for every currently registered plugin id, using the
    same cached `PluginLifecycle` instance `start_plugins()` created.
  - `AIEngine` introduces no lifecycle-guard logic of its own beyond
    what `PluginLifecycle` (`mellivor_kernel.plugins`,
    [ADR-0014](../adr/0014-plugin-runtime-foundation.md)) already
    enforces — an out-of-order call still raises exactly the
    `PluginLifecycleError` it always would.
  - **Each `PluginRegistry` may be owned by at most one live `AIEngine`
    at a time.** `AIEngine.__init__` raises `AIEngineError` if the
    `plugin_registry` it is given is already owned by another
    currently-live `AIEngine`. Two engines sharing one registry would
    each track that registry's plugins through independent
    `PluginLifecycle` objects wrapping the same live `Plugin`
    instances, silently double-`initialize()`ing them the moment both
    engines' `start_plugins()` ran. Ownership is tracked with weak
    references on both sides, so it is never a permanent lock: once the
    owning `AIEngine` is garbage collected, the same registry can back
    a new one.

## `AIEngineBuilder`

```python
class AIEngineBuilder:
    def __init__(self, runtime: RuntimeContext) -> None: ...

    def with_authorization(
        self,
        authorizer: Authorizer | None = None,
        *,
        audit_sink: AuditSink | None = None,
    ) -> AIEngineBuilder: ...
    def with_event_bus(self, event_bus: EventBus) -> AIEngineBuilder: ...
    def with_memory(self, memory: MemoryStore) -> AIEngineBuilder: ...
    def with_observability(self, sink: StructuredEventSink) -> AIEngineBuilder: ...
    def with_plugin_registry(self, registry: PluginRegistry) -> AIEngineBuilder: ...
    def with_plugin_discovery(
        self,
        root: Path | str,
        *,
        loader: PluginLoader | None = None,
    ) -> AIEngineBuilder: ...

    def build(self) -> AIEngine: ...
```

- Every `with_*` method returns `self` and only records the caller's
  intent; nothing is constructed until `build()` runs, exactly once, so
  calling `with_authorization()` before or after `with_event_bus()`
  produces an identical result — no method-call-ordering fragility.
- `with_authorization()` with no `authorizer` argument means "build a
  default `AuthorizationEngine`" (from the runtime's own
  `tool_registry`, wired to whichever `event_bus`/`audit_sink` were also
  configured by `build()` time); omitting `with_authorization()`
  entirely means no authorization is performed, matching
  `ExecutionEngine`'s own `authorizer=None`-means-disabled convention.
- `with_plugin_registry()` supplies the registry `build()` composes
  `AIEngine` with; omitting it creates a new, empty `PluginRegistry()`.
  The supplied registry must not already be owned by another
  currently-live `AIEngine` (see "Each `PluginRegistry` may be owned by
  at most one live `AIEngine` at a time" above) — `build()` raises
  `AIEngineError` if it is.
- `with_plugin_discovery(root)` runs
  `PluginDiscovery(loader).discover_and_register(root, plugin_registry)`
  during `build()`, against whichever `PluginRegistry` `build()` is
  using (the supplied one, or a fresh empty one). Any exception is
  wrapped in `AIEngineError` — the same exception `build()` also uses for
  a plugin-registry ownership violation, since both are construction-time
  failures of `build()` itself, never a runtime failure of a composed
  engine.
- `build()` returns a new `AIEngine` on every call, each with its own
  mutable plugin-lifecycle state — *unless* the same explicit
  `PluginRegistry` was supplied via `with_plugin_registry()` and an
  `AIEngine` from an earlier `build()` call on it is still live, in which
  case the second `build()` raises `AIEngineError` rather than silently
  producing a second owner for that registry.

## Exceptions

`ai_engine/exceptions.py` — subclasses `core.exceptions.KernelError`
directly, matching every existing subsystem's rule that exception
hierarchies never cross package boundaries.

- `AIEngineError` — the only exception this subsystem defines. Raised
  only for `AIEngineBuilder`/`AIEngine` construction-time failures: a
  wrapped plugin-discovery failure (from `build()`), or a `PluginRegistry`
  already owned by another live `AIEngine` (from `AIEngine.__init__`
  itself, so the invariant holds regardless of construction path). Never
  raised for a runtime failure of a composed engine —
  `execute()`/`run_workflow()`/`run_agent()` propagate exactly what
  `ExecutionEngine`/`WorkflowEngine`/`AgentEngine` themselves raise,
  unwrapped.

## Dependency relationship

```
ai_engine → core, bootstrap, execution, authorization, workflow, agents,
            memory, events, security, observability, plugins,
            plugin_discovery
```

`ai_engine` never depends on `config`, `providers`, `tools`,
`plugin_sdk`, or `plugins_builtin` directly. No other kernel package
imports `ai_engine` — it sits at the top of the composition stack; only
a consuming application (e.g. Mellivor One) is expected to depend on it.
