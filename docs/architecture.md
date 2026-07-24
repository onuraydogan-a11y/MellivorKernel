# Mellivor Kernel — High-Level Architecture

Status: Release Candidate (v0.13.0). `core`, `config`, `tools`,
`providers` (interfaces plus the `ClaudeProvider` reference
implementation), `bootstrap`, `execution`, `authorization`, `events`,
`memory`, `workflow`, a first slice of `agents`, and foundation-only
`security` and `observability` packages are implemented — see each
subsystem's entry below and its own spec in `docs/specs/` for what
"implemented" covers and excludes. `plugins` remains an unimplemented
skeleton; `agents` is a first, deliberately minimal slice; `security` and
`observability` are contracts-and-primitives-only foundations with no
concrete secret backend, authentication model, metrics/tracing vendor, or
telemetry export yet, and neither is consumed by any other subsystem yet.
See `docs/release/v1.0-release-checklist.md` for the full
release-readiness assessment.

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
  pluggable extensions to the kernel.

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
imported by `authorization`, `execution`, `workflow`, `agents`, or
`providers` — see [`docs/specs/security.md`](specs/security.md) and
[ADR-0012](adr/0012-security-foundation.md). This package is
foundation-only: it implements no authentication, OAuth, SSO, RBAC,
encryption, or concrete secret backend, and no subsystem consumes it yet.
Those remain unplaced.

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
[ADR-0013](adr/0013-observability-foundation.md). This package is
foundation-only: it ships no metrics backend, tracing vendor integration,
telemetry exporter, or audit/trace consumer built on `events`, and no
subsystem consumes it yet. Those remain unaddressed.

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
provider it might one day inform.

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

## Consumption model

Products — Mellivor One, and future enterprise products — depend on the
kernel as a library: they compose kernel subsystems and supply providers for
the model(s) they need. Business logic, UI, and domain modules live entirely
in the consuming product, never in this repository. As of Sprint 5, this
composition has a concrete mechanism — `mellivor_kernel.bootstrap` — rather
than being something each consuming product had to hand-roll itself.

## How this document evolves

Changes to subsystem boundaries, the kernel's responsibility list, or the
principles in [`docs/architecture/principles.md`](architecture/principles.md)
should be proposed and recorded as an ADR in [`docs/adr/`](adr/README.md)
before this document is updated to match.
