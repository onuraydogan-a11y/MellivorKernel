# 0018. AI Engine Foundation

Status: Accepted
Date: 2026-07-26

## Context

By Sprint 21 the kernel has every subsystem ADR-0002 names as a kernel
responsibility: `execution` (ADR-0006), `authorization` (ADR-0007),
`events` (ADR-0008), `memory` (ADR-0009), `workflow` (ADR-0010), `agents`
(ADR-0011), `security` (ADR-0012), `observability` (ADR-0013), `plugins`
(ADR-0014), `plugin_sdk` (ADR-0015), `plugins_builtin` (ADR-0016), and
`plugin_discovery` (ADR-0017) — plus `bootstrap`, which assembles
infrastructure (`config`, `core`, `providers`, `tools`) into a
`RuntimeContext`. Bootstrap deliberately stops there: it has never wired
`ExecutionEngine`, `WorkflowEngine`, `AgentEngine`, an `Authorizer`, or a
`PluginRegistry` together, on the documented reasoning (Sprint 17's own
release-checklist finding) that infrastructure assembly and
orchestration-chain composition are separate concerns.

The consequence: today, any consumer — starting with Mellivor One — that
wants to run a workflow or an agent must hand-construct `Dispatcher`,
`ExecutionEngine`, `WorkflowEngine`, and `AgentEngine` itself, wiring each
one's `Optional[...] = None` dependencies correctly, every time. Nothing
in the kernel is wrong; this is simply the one remaining gap between "the
kernel has every capability ADR-0002 names" and "a product can adopt the
kernel with a single, obvious entry point."

A Sprint 22 Architecture Challenge compared three candidates for this
slot — a second built-in plugin, an AI Engine Foundation, and an
additional provider — evaluated on dependency readiness, architectural
cohesion, customer/developer value, extensibility, implementation risk,
and impact on v1.0. AI Engine Foundation ranked highest: a second plugin
would exercise an already-proven path a second time without closing any
open gap, an additional provider only widens `providers/`, while the
composition gap above blocks every product adoption story until it is
closed, and every dependency it would need (`execution`, `workflow`,
`agents`, `authorization`, `plugins`, `bootstrap`) already exists and is
stable.

## Decision

Implement the **AI Engine Foundation** as a new top-level package,
`mellivor_kernel.ai_engine`, providing exactly one composed façade,
`AIEngine`, built only by a fluent builder, `AIEngineBuilder`, over an
already-bootstrapped `RuntimeContext` — introducing no new business
logic, chat features, prompting, reasoning, planning, orchestration
decisions, or provider-selection logic. `AIEngine` is a pure delegation
layer: every operation calls the exact method name of the existing engine
that already owns that decision, with exactly the arguments given, and
returns exactly what that engine returns.

**Package layout** — exactly five modules, no more:

- `exceptions.py` — `AIEngineError`, subclassing `core.exceptions.KernelError`
  directly. Raised only for `AIEngineBuilder`/`AIEngine` construction-time
  failures (a wrapped plugin-discovery failure, or a `PluginRegistry`
  already owned by another live `AIEngine` — see "Exclusive
  `PluginRegistry` ownership" below). Never raised for a runtime failure
  of a composed engine — `execute()`/`run_workflow()`/`run_agent()`
  propagate exactly what `ExecutionEngine`/`WorkflowEngine`/`AgentEngine`
  themselves raise or return, never re-wrapped.
- `context.py` — `AIEngineContext`, a frozen dataclass holding the four
  fields every kernel-scoped context already carries (`configuration`,
  `logger`, `runtime`, `services`), plus `to_execution_context()`,
  `to_workflow_context()` (wraps a fresh `to_execution_context()`),
  `to_agent_context()` (wraps a fresh `to_workflow_context()`), and
  `to_plugin_context()` — one constructor per context shape an existing
  engine already accepts, introducing no new context shape of its own.
  Internal only — not exported from `__init__.py`; see "`AIEngineContext`
  is internal-only" below.
- `engine.py` — `AIEngine`. Exposes only `.runtime` and `.plugin_registry`
  as read-only properties — never the composed `ExecutionEngine`/
  `WorkflowEngine`/`AgentEngine`/`Authorizer` themselves; see "No public
  engine accessors" below. `execute()`/`run_workflow()`/`run_agent()` as
  pure delegation; `execution_context()`/`workflow_context()`/
  `agent_context()`/`plugin_context()` as context builders; and
  `start_plugins()`/`stop_plugins()`/`dispose_plugins()` as the one
  lifecycle `AIEngine` does own — a plugin is the only thing composed
  here with a lifecycle contract of its own, since the underlying
  `Kernel`'s lifecycle already ran to completion inside
  `BootstrapBuilder.build()`, before an `AIEngine` ever exists. Plugin
  lifecycle re-reads `plugin_registry.enumerate()` on every call (a
  plugin registered after construction is still picked up) and reuses one
  `PluginLifecycle` per plugin id for the `AIEngine`'s lifetime, so a
  previously-stopped plugin is restarted via `PluginLifecycle.start()`
  directly rather than re-`initialize()`d. Each `PluginRegistry` may be
  owned by at most one live `AIEngine` at a time, enforced in
  `AIEngine.__init__` itself; see "Exclusive `PluginRegistry` ownership"
  below.
- `builder.py` — `AIEngineBuilder(runtime)`. Fluent `with_authorization()`
  /`with_event_bus()`/`with_memory()`/`with_observability()`/
  `with_plugin_registry()`/`with_plugin_discovery()`, each returning
  `self`; every optional piece stays optional and explicit, matching each
  composed engine's own `None`-means-disabled convention. All accumulated
  state is assembled exactly once, inside `build()` — `with_authorization()`
  only records the request, deferring `AuthorizationEngine` construction
  to `build()`, so calling `with_authorization()` before or after
  `with_event_bus()` produces an identical result.
- `__init__.py` — re-exports `AIEngine`, `AIEngineBuilder`,
  `AIEngineError`. Nothing else is public.

**Resolving the wrapped-`Kernel` constraint without touching `bootstrap`.**
`RuntimeContext` deliberately never exposes the `Kernel` it wraps (its own
docstring: "There is no way to recover the wrapped Kernel instance from a
RuntimeContext"). `AIEngineContext.runtime` is obtained by calling the
already-public `RuntimeContext.execution_context()` and reading `.runtime`
off the `ExecutionContext` it returns — zero changes to `bootstrap` were
needed, keeping this sprint strictly additive.

**Exclusive `PluginRegistry` ownership.** `with_plugin_registry()` is a
fully public path for pointing two different `AIEngine` instances at the
same registry. Left unguarded, each engine would track that registry's
plugins through its own independent `PluginLifecycle` objects wrapping
the same live `Plugin` instances — the moment both engines' own
`start_plugins()` ran, each would believe its own plugin was still
`REGISTERED` and call `initialize()` on it a second time, defeating the
one guarantee `PluginLifecycle` exists to provide. `AIEngine.__init__`
now tracks ownership in a module-level `weakref.WeakKeyDictionary`
keyed by `PluginRegistry` instance, raising `AIEngineError` if the
registry it is given is already owned by another currently-live
`AIEngine`. Both sides of the mapping are weak: ownership is never a
permanent lock, only an exclusivity guarantee for as long as both the
registry and its owning engine are alive — once the owning `AIEngine` is
garbage collected, the same registry can back a new one. Enforced in
`AIEngine.__init__` itself, not only in `AIEngineBuilder.build()`, so the
invariant holds regardless of construction path.

**No public engine accessors.** The original design exposed
`.execution_engine`, `.workflow_engine`, `.agent_engine`, and
`.authorizer` as read-only properties. Each let a caller reach past
`execute()`/`run_workflow()`/`run_agent()` and call the underlying engine
directly — harmless today, since there is no policy on top of them to
bypass, but a compatibility trap the moment there is: once external code
depends on the direct path, removing it becomes a breaking change,
foreclosing any future ability to add engine-level behavior (metrics,
additional guards) without one. All four are removed before this sprint
ships. `.plugin_registry` stays public because it is not a bypass of any
`AIEngine` method — it is the object other code registers plugins into
before calling `start_plugins()`, which `AIEngine` has no method of its
own to do.

**`AIEngineContext` is internal-only.** No supported code path ever
returns one to a consumer — `AIEngine`'s own context-builder methods
return `ExecutionContext`/`WorkflowContext`/`AgentContext`/
`PluginContext`, never `AIEngineContext` itself — and constructing one
directly requires a raw `Kernel`, obtainable only by replaying the same
`RuntimeContext.execution_context().runtime` indirection `ai_engine`
itself uses internally. It is therefore no longer exported from
`__init__.py`; it remains an ordinary class in `ai_engine.context`, used
internally by `builder.py`/`engine.py` and directly importable by this
package's own tests, but carries no public compatibility guarantee.

**Dependency boundary.** `ai_engine` depends on `core`, `bootstrap`,
`execution`, `authorization`, `workflow`, `agents`, `memory`, `events`,
`security`, `observability`, `plugins`, and `plugin_discovery` — never on
`config`, `providers`, `tools`, `plugin_sdk`, or `plugins_builtin`
directly. Nothing in the kernel imports `ai_engine`; it sits strictly
above every package it depends on, the top of the composition stack, with
no dependents inside this repository — only a consuming application (e.g.
Mellivor One) is expected to depend on it.

**Explicitly out of scope**, matching this sprint's own instructions: any
business logic, chat feature, prompting, reasoning, planning, or
orchestration decision; provider-selection logic; anything that
duplicates `bootstrap`, `ExecutionEngine`, `WorkflowEngine`, or
`AgentEngine`.

## Self-critique, restated as decision record

- **Does this duplicate Bootstrap?** No. `bootstrap` remains solely
  responsible for infrastructure assembly (`config`/`core`/`providers`/
  `tools` → `RuntimeContext`); `ai_engine` never constructs a `Kernel`,
  `ProviderRegistry`, or `ToolRegistry` — it only composes on top of an
  already-built `RuntimeContext`, the same one-way dependency direction
  `workflow`→`execution` and `agents`→`workflow` already established.
- **Does this violate ADR-0002?** No. ADR-0002 fixes the kernel's
  *capability* list; `ai_engine` adds no new capability to it — it
  composes existing capabilities (`execution`, `workflow`, `agents`,
  `plugins`) that already appear on that list into one entry point.
- **Does this increase coupling?** It adds one new dependency edge
  (products → `ai_engine`) but removes none and adds no edge *between*
  existing packages — every existing package's own dependency graph is
  unchanged, verified by the AST-based dependency-rules tests this sprint
  adds.
- **Is there a simpler architecture?** A thinner alternative — a single
  free function assembling the chain — was considered and rejected: it
  cannot hold `with_*` optional configuration without either a long
  parameter list or losing the order-independent deferred-construction
  property `AIEngineBuilder` gives for free, the same reasoning that
  already justified `BootstrapBuilder` over a free function.
- **Could Mellivor One be built directly on Kernel without this
  package?** Yes, mechanically — every dependency `ai_engine` composes is
  already public. **Why it should still exist:** without it, every
  product repeats the same `Dispatcher`→`ExecutionEngine`→
  `WorkflowEngine`→`AgentEngine` wiring, with every optional
  authorization/event/memory/observability argument threaded through by
  hand — exactly the "capability... rebuilt, slightly differently, inside
  each product" this kernel's mission statement exists to prevent.

## Alternatives considered

- **Fold this composition directly into `bootstrap`.** Rejected:
  `bootstrap`'s own scope (infrastructure assembly) is already documented
  and stable; growing it to also own orchestration-chain composition
  would blur that boundary and make `RuntimeContext` responsible for two
  unrelated lifecycles (kernel infrastructure vs. plugin fleet).
- **A second built-in plugin (this sprint's alternative candidate).**
  Rejected by the Architecture Challenge: it exercises an already-proven
  path (Loader→Registry→Lifecycle) a second time without closing the
  composition gap blocking product adoption.
- **An additional provider foundation (this sprint's other alternative
  candidate).** Rejected: widens `providers/` alone, with no bearing on
  the orchestration-composition gap, and no dependency of it was blocking
  anything else.
- **A single free function (`build_ai_engine(runtime, **kwargs)`) instead
  of a builder.** Rejected: loses order-independent, deferred
  construction and does not scale to future optional pieces without
  either a growing parameter list or breaking callers, unlike the
  `with_*` chain.

## Consequences

- A consuming application now has exactly one supported way to go from a
  bootstrapped `RuntimeContext` to a fully composed orchestration chain:
  `AIEngineBuilder(runtime).with_*(...).build()`. No product needs to
  hand-wire `Dispatcher`/`ExecutionEngine`/`WorkflowEngine`/`AgentEngine`
  again.
- No behavioral change to any existing package: `ai_engine` has zero
  dependents inside this repository and its only dependency edges are to
  already-stable packages, none of them modified.
- Plugin lifecycle management moves to `AIEngine` for any consumer that
  adopts it, but `plugins.PluginLifecycle` itself is unchanged and remains
  independently usable, exactly as `plugin_discovery` already depends on
  it without depending on `ai_engine`.
- A future product-facing SDK, a richer plugin-fleet API (bulk
  start/stop with partial-failure reporting), and multi-tenant runtime
  composition remain open, tracked as future work — this ADR does not
  authorize or schedule them.
