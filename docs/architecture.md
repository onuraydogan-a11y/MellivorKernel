# Mellivor Kernel — High-Level Architecture

Status: Release Candidate (v0.13.0). `core`, `config`, `tools`,
`providers` (interfaces plus the `ClaudeProvider` reference
implementation), `bootstrap`, `execution`, `authorization`, `events`,
`memory`, `workflow`, a first slice of `agents`, and foundation-only
`security`, `observability`, `plugins`, `plugin_sdk`, `plugins_builtin`,
`plugin_discovery`, and `ai_engine` packages are implemented — see each
subsystem's entry below and its own spec in `docs/specs/` for what
"implemented" covers and excludes. `agents` is a first, deliberately
minimal slice; `security` and `observability` are
contracts-and-primitives-only foundations with no concrete secret
backend, authentication model, metrics/tracing vendor, or telemetry
export yet; `plugin_sdk` is a developer-convenience layer over `plugins`
adding no new contract or validation rule of its own; `plugins_builtin`
contains exactly one built-in plugin (`SystemInfoPlugin`, Sprint 20),
exercising both foundations end to end; `plugin_discovery` (Sprint 21)
discovers plugins from a filesystem location and loads/registers them
through the unmodified `PluginLoader`/`PluginRegistry`, introducing no
new marketplace, remote-plugin, sandboxing, hot-reload,
signature-verification, or package-installation capability; `ai_engine`
(Sprint 22) is a pure composition layer, `AIEngineBuilder`/`AIEngine`,
assembling an already-bootstrapped `RuntimeContext` and the
orchestration-chain engines (`execution`/`workflow`/`agents`, with
`authorization` optionally consulted) plus a `PluginRegistry`, with no
new business logic, chat feature, prompting, reasoning, planning,
orchestration decision, or provider-selection logic of its own. As of
Sprint 17, the security/observability foundations have their first
production consumers — `authorization` records grant/deny decisions
through `security.AuditSink`, and `execution` emits lifecycle
observations through `observability.StructuredEventSink` — but no other
subsystem consumes either. As of Sprint 20, `plugin_sdk`'s first
consumer is `plugins_builtin`. As of Sprint 21, `plugin_discovery` is
the first consumer to load a plugin (`plugins_builtin.SystemInfoPlugin`)
without a caller hand-constructing its manifest. As of Sprint 22,
`ai_engine` is the first consumer to compose `execution`, `workflow`,
`agents`, and `authorization` together into one object; nothing in the
kernel itself consumes `ai_engine`, `plugin_discovery`, or
`plugins_builtin` — only a consuming application is expected to. See
`docs/release/v1.0-release-checklist.md` for the full release-readiness
assessment.

This document reflects the scope decision recorded in
[ADR-0002](adr/0002-ai-enterprise-kernel-scope-and-subsystems.md). Read that
ADR for the full rationale; this document tracks its current-state summary.

## What the kernel is

Mellivor Kernel is an **AI Enterprise Kernel**, not a software development
framework. Its purpose is to power enterprise AI applications — starting with
Mellivor One — by providing the AI substrate those applications are built on.

## What the kernel is not

The kernel is strictly **business-agnostic**. It must never contain CRM,
Legal, HR, Finance, Security, or any other business/domain logic. That logic
always lives in external, consuming applications. Nothing in this repository
should assume, encode, or special-case any business vertical.

## Guiding principles

See [`docs/architecture/principles.md`](architecture/principles.md) for the
kernel's guiding principles (moved there in Sprint 5's docs
reorganization).

## Kernel responsibilities

Per ADR-0002, the kernel's responsibilities are limited to exactly:

- AI orchestration
- Agent lifecycle
- Workflow engine
- Memory abstraction
- Tool execution
- Event bus
- Plugin loading
- Multi-LLM provider abstraction
- Configuration
- Observability
- Security primitives

## Subsystems (`src/mellivor_kernel/`)

```
                 ┌─────────────────────────────┐
                 │             core             │
                 │   lifecycle, contracts,      │
                 │   dependency boundaries      │
                 └───────────────┬───────────────┘
                                  │
   ┌─────────┬─────────┬─────────┼─────────┬─────────┬─────────┐
   │          │          │         │          │          │          │
┌──▼───┐ ┌───▼────┐ ┌───▼───┐ ┌──▼───┐ ┌───▼────┐ ┌───▼───┐ ┌───▼───┐
│agents│ │workflow│ │memory │ │tools │ │ events │ │plugins│ │ config│
└──┬───┘ └───┬────┘ └───┬───┘ └──┬───┘ └───┬────┘ └───┬───┘ └───┬───┘
   │          │          │         │          │          │          │
   └──────────┴──────────┴────┬────┴──────────┴──────────┴──────────┘
                                │
                          ┌─────▼──────┐
                          │  providers  │
                          │ (multi-LLM, │
                          │  external   │
                          │  systems)   │
                          └─────────────┘
```

- **`core`** — Kernel bootstrapping and lifecycle, shared contracts/types,
  dependency-injection boundaries. The only subsystem every other subsystem
  may depend on.

- **`agents`** — Agent lifecycle: creation, state, execution, and teardown of
  individual AI agents, independent of any single model provider. Agent
  Runtime Core implemented in Sprint 13A (`Agent`, `AgentDefinition`,
  `AgentContext`, `AgentEngine`, `AgentResult`) — like `events`, `memory`,
  and `workflow` before it, this responsibility already had its
  designated package from ADR-0002; Sprint 13A only began filling it in.
  Deliberately minimal: an agent invokes exactly one workflow by
  delegating entirely to `workflow.WorkflowEngine` — no planning,
  reasoning, reflection, or multi-agent composition yet. See
  [`docs/specs/agents.md`](specs/agents.md) and
  [ADR-0011](adr/0011-agent-runtime-core-and-orchestration-chain.md).

- **`workflow`** — The workflow engine: composing multiple execution steps
  into a sequential process. Implemented in Sprint 12 (`Workflow`,
  `WorkflowDefinition`, `WorkflowStep`, `WorkflowEngine`) — like `events`
  and `memory` before it, this responsibility already had its designated
  package from ADR-0002; Sprint 12 only filled it in. Composes calls to
  `execution.ExecutionEngine` only — it never touches a tool or provider
  directly, and no scheduling, cron, or parallel steps are implemented.
  See [`docs/specs/workflow.md`](specs/workflow.md) and
  [ADR-0010](adr/0010-workflow-engine-and-orchestration-boundary.md).

- **`memory`** — Memory abstraction: contracts for short-term
  (session/conversation) and long-term (persistent, retrievable) memory,
  without committing to a specific store. Implemented in Sprint 11
  (`Memory`, `MemoryStore`, `InMemoryStore`) for **text memory only** —
  no embeddings, vector database, semantic search, RAG, or persistence
  yet. Like `events` in Sprint 9, this responsibility already had its
  designated package from ADR-0002; Sprint 11 only filled it in. See
  [`docs/specs/memory.md`](specs/memory.md) and
  [ADR-0009](adr/0009-memory-subsystem-and-execution-recording.md).

- **`tools`** — Tool execution: registration, invocation, input/output
  schemas, and execution boundaries (including sandboxing concerns) for
  anything the kernel can call out to.

- **`events`** — The event bus: publish/subscribe primitives used for
  communication between kernel subsystems and, indirectly, between agents
  and workflows. Implemented in Sprint 9 (`Event`, `EventBus`,
  `InMemoryEventBus`) — unlike "AI orchestration" and "Security
  primitives" below, this responsibility already had its designated
  package from ADR-0002; Sprint 9 only filled it in. See
  [`docs/specs/events.md`](specs/events.md) and
  [ADR-0008](adr/0008-event-bus-and-lifecycle-events.md).

- **`plugins`** — Plugin loading: discovery, registration, and lifecycle of
  pluggable extensions to the kernel. The runtime foundation — contracts
  (`Plugin`, `PluginMetadata`, `PluginContext`, `PluginCapability`), an
  immutable `PluginManifest`, `PluginRegistry`, `PluginLoader`, and
  `PluginLifecycle` state management — was implemented in Sprint 18.
  A caller may still supply an explicit `PluginManifest` and constructor
  directly. A developer-convenience layer over this runtime, `plugin_sdk`,
  was added in Sprint 19 — see "The Plugin SDK" section below. The
  kernel's first (and, at this sprint's scope, only) built-in plugin,
  `plugins_builtin.SystemInfoPlugin`, was added in Sprint 20 — see
  "Built-in plugins" below. Filesystem discovery, `plugin_discovery`, was
  added in Sprint 21 — see "Plugin Discovery" below. No marketplace,
  remote plugins, sandboxing, hot reload, signature verification, or
  package installation is implemented. See
  [`docs/specs/plugins.md`](specs/plugins.md) and
  [ADR-0014](adr/0014-plugin-runtime-foundation.md).

- **`config`** — Configuration: contracts for configuration and environment
  loading (including feature flags), kept separate so products can supply
  their own configuration sources without the kernel assuming any one
  mechanism.

- **`providers`** — Multi-LLM provider abstraction: pluggable integrations to
  model providers and related external systems. This is the only place
  provider-specific code is allowed to live; providers implement contracts
  defined by the other subsystems and are swappable and independently
  versioned. The interface (`BaseProvider`, `ProviderRegistry`,
  `ProviderFactory`) shipped in Sprint 3; the first concrete
  implementation, `providers.claude.ClaudeProvider` (Anthropic Messages
  API), shipped in Sprint 10 with no change to that interface — see
  [`docs/specs/providers.md`](specs/providers.md).

### AI orchestration: placed in `execution` (Sprint 6)

Per [ADR-0006](adr/0006-execution-core-orchestration-layer.md), the
**AI orchestration** responsibility named above is implemented by
`execution`, a top-level package alongside `bootstrap` rather than one of
the seven subsystems in the diagram: it orchestrates *running* work across
`tools` and `providers` (dispatch, execution lifecycle), the same way
`bootstrap` composes them into a running kernel. `execution` depends on
`tools` and `providers`; neither depends back on it.

### Security primitives: `authorization` (Sprint 8) plus a `security` foundation (Sprint 15)

Per [ADR-0007](adr/0007-authorization-engine-and-execution-decoupling.md),
a slice of the **Security primitives** responsibility — deciding whether an
execution request is authorized — is implemented by `authorization`, a
top-level package that depends on `execution` (for its
`target`/`operation` vocabulary) and `tools` (for the existing permission
model), never the other way around: `execution` consults it only through
the small `Authorizer`/`AuthorizationOutcome` Protocols defined in
`execution.contracts`, so `execution` never imports `authorization`.

As of Sprint 15, a second, structurally separate slice of the same
responsibility is implemented by `security` — a top-level,
dependency-injected package providing secret handling (`Secret`,
`SecretProvider`, `SecretProviderRegistry`), a structural policy contract
(`SecurityPolicy`, `SecurityDecision`), a secure-configuration contract
(`SecureConfiguration`), and audit contracts (`AuditRecord`, `AuditSink`).
It depends only on `core` (for the shared `KernelError` base) and is not
imported by `execution`, `workflow`, `agents`, or `providers` — see
[`docs/specs/security.md`](specs/security.md) and
[ADR-0012](adr/0012-security-foundation.md). This package remains
foundation-only: it implements no authentication, OAuth, SSO, RBAC,
encryption, or concrete secret backend. As of Sprint 17, `authorization`
is its first consumer, recording every grant/deny decision as an
`AuditRecord` through an injected `AuditSink` — see the authorization
layer section below. Everything beyond that (a concrete audit sink
implementation, authentication, encryption) remains unplaced.

### Observability: structured logging (Sprint 2) plus an `observability` foundation (Sprint 16)

Structured logging — the first slice of the Observability responsibility —
is implemented in `core/logging.py` (Sprint 2), using the fallback ADR-0002
itself anticipated ("hosted inside `core/`") rather than a new top-level
package.

As of Sprint 16, a second slice is implemented by `observability` — a
top-level, dependency-injected package providing correlation/trace
metadata (`ObservationContext`), metrics and tracing protocols
(`MetricsRecorder`, `TraceRecorder`/`TraceSpan`), a structured-event
protocol (`StructuredEventSink`/`StructuredObservationEvent`), no-op
default implementations, and an `Observability` composition wrapper. Unlike
every other subsystem in this document, it has no dependency on any other
kernel package, including `core` — see
[`docs/specs/observability.md`](specs/observability.md) and
[ADR-0013](adr/0013-observability-foundation.md). This package remains
foundation-only: it ships no metrics backend, tracing vendor integration,
or telemetry exporter. As of Sprint 17, `execution` is its first
consumer, emitting a `StructuredObservationEvent` at each lifecycle point
through an injected `StructuredEventSink` — see the execution layer
section below. Everything beyond that (a concrete metrics/tracing
backend, vendor integration, or an audit/trace consumer built on
`events`) remains unaddressed.

## The composition layer (`src/mellivor_kernel/bootstrap/`)

`core` owns the kernel runtime's own bootstrap/lifecycle sequence
(`core.runtime.Kernel.start()`/`.shutdown()`), consistent with its
description above. Composing multiple subsystems together into one running
kernel is a distinct, higher-level concern that cannot live inside `core`
(or any single subsystem) without that subsystem depending on its siblings
— which would break the acyclic dependency graph the subsystems otherwise
maintain (`core` depends on nothing else; `config`/`providers`/`tools` each
depend only on `core`).

`bootstrap` is a top-level package, a peer to the subsystems above rather
than one of them, that assembles `config` + `core` + `providers` + `tools`
into a running kernel (`KernelBootstrap`, `BootstrapBuilder`) and exposes a
read-only view of the result (`RuntimeContext`) to consumers. It is not a
new kernel *responsibility* under the list above — it composes
responsibilities that already exist — so its addition did not require
amending that list. As of Sprint 7, `RuntimeContext` also builds an
`execution.ExecutionContext` (`.execution_context()`), the same way it
already built a `tools.ToolContext` (`.tool_context()`) — see
[`docs/specs/bootstrap.md`](specs/bootstrap.md).

## The execution layer (`src/mellivor_kernel/execution/`)

`execution` is a top-level package, a peer to `bootstrap` rather than one of
the subsystems above, that orchestrates execution across them: an
`ExecutionEngine` validates and runs an `ExecutionRequest` by dispatching it
(`Dispatcher`) to the Tool Runtime or the Provider Runtime and returning a
common `ExecutionResult`. See
[`docs/specs/execution.md`](specs/execution.md) and
[ADR-0006](adr/0006-execution-core-orchestration-layer.md) for the full
contract and the rationale for placing it here rather than inside `tools`
or `providers`.

Execution Core is orchestration only: retries and workflow composition
remain future work — `execution` does not anticipate their shape. As of
Sprint 8, authorization is no longer future work (see below), but
`execution` still does not perform it itself. As of Sprint 9, `execution`
publishes its own lifecycle events (`ExecutionStarted`, `ExecutionCompleted`,
`ExecutionFailed`) to an injected `events.EventBus` — see
[ADR-0008](adr/0008-event-bus-and-lifecycle-events.md) — but still depends
only on the abstract bus, never a concrete implementation. As of Sprint
11, `execution` optionally records each outcome to an injected
`memory.MemoryStore` — see
[ADR-0009](adr/0009-memory-subsystem-and-execution-recording.md) — the
only new dependency this adds is on `memory` itself, never on any
provider it might one day inform. As of Sprint 17, `execution` also
optionally emits a `StructuredObservationEvent` to an injected
`observability.StructuredEventSink` at the same three lifecycle points
`EventBus` already publishes to, correlated by `request.request_id` — the
two mechanisms are independent, and configuring one never affects the
other. This is the first subsystem to consume `observability` since its
Sprint 16 foundation shipped — see
[ADR-0013](adr/0013-observability-foundation.md) and
[`docs/specs/execution.md`](specs/execution.md).

## The authorization layer (`src/mellivor_kernel/authorization/`)

`authorization` is a top-level package that decides only whether an
`ExecutionRequest` is authorized to proceed to dispatch — it never
executes and never dispatches. Unlike every other cross-subsystem
dependency described in this document, the dependency here runs from the
newer package to the established one: `authorization` depends on
`execution` (and `tools`, for the existing permission model), while
`execution` depends on neither — it consults authorization only through a
small structural contract (`execution.contracts.Authorizer`), the same
dependency-inversion pattern `core.contracts.KernelSettings` established
in Sprint 2. See [`docs/specs/authorization.md`](specs/authorization.md)
and [ADR-0007](adr/0007-authorization-engine-and-execution-decoupling.md).

As of Sprint 9, `authorization` also publishes `AuthorizationGranted`/
`AuthorizationDenied` to the same injected `events.EventBus` `execution`
uses — a normal dependency on generic infrastructure, not the kind of
coupling ADR-0007 inverted away from, since `events` carries no decision
logic. See [ADR-0008](adr/0008-event-bus-and-lifecycle-events.md).

As of Sprint 17, `authorization` also optionally records every grant/deny
decision as a `security.AuditRecord` to an injected `security.AuditSink`,
alongside (never instead of) the `EventBus` publication above — the two
mechanisms are independent, and configuring one never affects the other.
This is the first subsystem to consume `security` since its Sprint 15
foundation shipped — see [ADR-0012](adr/0012-security-foundation.md) and
[`docs/specs/authorization.md`](specs/authorization.md).

As of Sprint 12, `workflow` sits above all of the above, composing
sequential `execution.ExecutionEngine.execute()` calls — it never
touches a tool, provider, or `Dispatcher` directly, and `execution` has
no dependency back on it. See [`docs/specs/workflow.md`](specs/workflow.md)
and [ADR-0010](adr/0010-workflow-engine-and-orchestration-boundary.md).

As of Sprint 13A, `agents` sits above `workflow`, invoking exactly one
`workflow.WorkflowDefinition` per agent run by delegating entirely to
`WorkflowEngine.run()` — `agents` has no dependency on `execution`,
`authorization`, `tools`, or `providers` at all, and `workflow` has no
dependency back on `agents`. The full chain is now
Agent → Workflow → Execution → Tool/Provider, one direction only. See
[`docs/specs/agents.md`](specs/agents.md) and
[ADR-0011](adr/0011-agent-runtime-core-and-orchestration-chain.md).

## The Plugin SDK (`src/mellivor_kernel/plugin_sdk/`)

`plugin_sdk` is a top-level package, a peer to `bootstrap`/`execution`
rather than one of the seven subsystems in the diagram above, implemented
in Sprint 19: a developer-facing convenience layer over the Plugin
Runtime Foundation (`plugins`, Sprint 18). It does not add any new
contract, validation rule, or capability — `PluginBuilder` and the
`create_*` helpers construct `PluginManifest`/`PluginMetadata`/
`PluginCapability` by delegating directly to those classes' own
constructors, `BasePlugin` supplies no-op lifecycle defaults over the
same `Plugin` contract, and the `is_valid_*` helpers catch
`PluginValidationError` rather than re-implementing any check. See
[`docs/specs/plugin_sdk.md`](specs/plugin_sdk.md) and
[ADR-0015](adr/0015-plugin-sdk-foundation.md).

`plugin_sdk` depends only on `plugins` (and, where needed, `core`) —
never on `execution`, `providers`, `workflow`, `authorization`, `memory`,
`observability`, `security`, or `bootstrap`. As of Sprint 20, its one
known dependent is `plugins_builtin` (below); no other subsystem imports
it. `plugin_sdk` itself adds no discovery, marketplace, or sandboxing
capability — filesystem discovery was placed in a separate package,
`plugin_discovery`, in Sprint 21 (below), unchanged from ADR-0014's
original scope decision.

## Built-in plugins (`src/mellivor_kernel/plugins_builtin/`)

`plugins_builtin` is a top-level package, implemented in Sprint 20,
exported separately from `plugins`/`plugin_sdk` the same way
`tools.builtin` is exported separately from `tools`. It contains exactly
one built-in plugin, `SystemInfoPlugin`, which exposes read-only kernel
information (kernel version, build info, available capabilities,
registered providers/tools, and runtime health) and demonstrates
`BasePlugin`'s "override only when necessary" design directly — it
overrides only `metadata` and `initialize()`, leaving `start()`/`stop()`/
`dispose()` as `BasePlugin`'s inherited no-ops. It performs no
configuration change and no mutation. See
[`docs/specs/plugins_builtin.md`](specs/plugins_builtin.md),
[`examples/plugin_system_info.py`](../examples/plugin_system_info.py),
and [ADR-0016](adr/0016-system-info-built-in-plugin.md).

Unlike `plugins`/`plugin_sdk`, `plugins_builtin` carries no dependency
ceiling of its own: it depends on `plugin_sdk`, `plugins`, `providers`
(to report registered providers), `tools` (to report registered tools),
`core`, and the top-level `version` module — the same latitude
`tools.builtin.HealthCheckTool` already has for `Kernel.health()`.
Nothing depends on `plugins_builtin`. `bootstrap` does not compose it,
consistent with every engine and plugin-runtime package shipped since
Sprint 6.

## Plugin Discovery (`src/mellivor_kernel/plugin_discovery/`)

`plugin_discovery` is a top-level package, implemented in Sprint 21,
providing exactly one class, `PluginDiscovery`, that discovers plugins
from a filesystem location and loads/registers them through the
*existing*, unmodified `plugins.PluginLoader`/`PluginRegistry` —
introducing no new loading, validation, or registration logic of its
own. `root` contains one subdirectory per plugin, each holding a
manifest file (a JSON object with `PluginManifest`'s own fields plus a
discovery-only `entry_point` string naming the zero-argument callable
that constructs the `Plugin`). `scan()`, `read_manifest()`, `load()`,
and `discover_and_register()` are each a single step, composable
independently; `discover_and_register()` fails fast, aborting on the
first error without rolling back plugins already registered. See
[`docs/specs/plugin_discovery.md`](specs/plugin_discovery.md),
[`examples/plugin_discovery.py`](../examples/plugin_discovery.py), and
[ADR-0017](adr/0017-plugin-discovery-foundation.md).

`plugin_discovery` depends only on `plugins` and `core` — never on
`providers`, `tools`, `execution`, `authorization`, `events`, `memory`,
`workflow`, `agents`, `security`, `observability`, `bootstrap`,
`plugin_sdk`, or `plugins_builtin`. Nothing depends on it. `bootstrap`
does not compose it, consistent with every plugin-runtime package
shipped since Sprint 18. No marketplace, remote plugins, sandboxing, hot
reload, signature verification, or package installation is implemented
— a discovered plugin's code is imported and executed with exactly the
same trust as any other import in the running process.
Nothing depends on `plugins_builtin`. `bootstrap` does not compose it,
consistent with every engine and plugin-runtime package shipped since
Sprint 6.

## AI Engine Foundation (`src/mellivor_kernel/ai_engine/`)

`ai_engine` is a top-level package, implemented in Sprint 22, providing
exactly one composed façade, `AIEngine`, built only by a fluent builder,
`AIEngineBuilder`, over an already-bootstrapped `RuntimeContext`. It
closes the one remaining gap between "the kernel has every capability
ADR-0002 names" and "a product can adopt the kernel with a single,
obvious entry point": until this sprint, any consumer wanting to run a
workflow or an agent had to hand-construct `Dispatcher`,
`ExecutionEngine`, `WorkflowEngine`, and `AgentEngine` itself, wiring
each one's optional dependencies correctly every time. `AIEngine`
introduces no new decision logic — `execute()`/`run_workflow()`/
`run_agent()` call exactly `ExecutionEngine.execute()`/
`WorkflowEngine.run()`/`AgentEngine.execute()`, with exactly the
arguments given, and return exactly what that engine returns. The one
lifecycle it does own is a composed `PluginRegistry`'s fleet
(`start_plugins()`/`stop_plugins()`/`dispose_plugins()`), since the
underlying `Kernel`'s own lifecycle already ran to completion inside
`BootstrapBuilder.build()` before an `AIEngine` exists. See
[`docs/specs/ai_engine.md`](specs/ai_engine.md) and
[ADR-0018](adr/0018-ai-engine-foundation.md).

`ai_engine` depends on `core`, `bootstrap`, `execution`, `authorization`,
`workflow`, `agents`, `memory`, `events`, `security`, `observability`,
`plugins`, and `plugin_discovery` — never on `config`, `providers`,
`tools`, `plugin_sdk`, or `plugins_builtin` directly. Nothing in the
kernel imports `ai_engine`; it sits at the top of the composition stack,
with no dependents inside this repository — only a consuming
application (e.g. Mellivor One) is expected to depend on it. `bootstrap`
remains solely responsible for infrastructure assembly
(`config`/`core`/`providers`/`tools` → `RuntimeContext`); `ai_engine`
never constructs a `Kernel`, `ProviderRegistry`, or `ToolRegistry` — it
only composes on top of an already-built `RuntimeContext`.

## Consumption model

Products — Mellivor One, and future enterprise products — depend on the
kernel as a library: they compose kernel subsystems and supply providers for
the model(s) they need. Business logic, UI, and domain modules live entirely
in the consuming product, never in this repository. As of Sprint 5, this
composition has a concrete mechanism — `mellivor_kernel.bootstrap` — rather
than being something each consuming product had to hand-roll itself. As of
Sprint 22, a product wanting the full orchestration chain on top of that
runtime has a second concrete mechanism — `mellivor_kernel.ai_engine` —
rather than hand-wiring `ExecutionEngine`/`WorkflowEngine`/`AgentEngine`
itself.

## How this document evolves

Changes to subsystem boundaries, the kernel's responsibility list, or the
principles in [`docs/architecture/principles.md`](architecture/principles.md)
should be proposed and recorded as an ADR in [`docs/adr/`](adr/README.md)
before this document is updated to match.
