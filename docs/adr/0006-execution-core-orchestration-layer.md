# 0006. Execution Core as the kernel's orchestration layer

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names **AI
orchestration** as one of the kernel's fixed responsibilities, but — unlike
`agents`, `workflow`, `memory`, `tools`, `events`, `plugins`, `config`, and
`providers` — it was never mapped to a package. `tools` and `providers` (as
of Sprint 5) each expose their own way to run something (`ToolExecutionPipeline`,
`BaseProvider.invoke`), but there was no shared entry point, no shared
result type, and no shared execution-lifetime context across them. Every
future consumer of execution (a workflow step, an agent action) would
otherwise have had to know the calling convention of each target subsystem
individually, and `workflow`/`agents` would each reinvent request/result
types that mean the same thing.

This sprint implements that missing responsibility as its own subsystem —
**Execution Core** — rather than leaving orchestration split across ad hoc
call sites. Per [`docs/adr/README.md`](README.md), this requires an ADR on
two counts: it introduces a new kernel subsystem, and it defines contracts
(`ExecutionRequest`, `ExecutionContext`, `ExecutionResult`) that `tools`,
`providers`, and (later) `workflow` and `agents` will depend on.

## Decision

**A new top-level package, `src/mellivor_kernel/execution/`, implements the
"AI orchestration" responsibility named in ADR-0002.** It sits alongside
`bootstrap` as a composing layer: `bootstrap` assembles subsystems into a
running kernel, `execution` orchestrates running work across them.

**Execution Core is execution-orchestration only.** It does not perform
authorization, retries, workflow composition, or anything else that isn't
directly "take a request, dispatch it, return a result":

- `ExecutionRequest` — an immutable dataclass carrying only execution
  metadata (`target`, `operation`, `payload`, `request_id`). No business
  state.
- `ExecutionContext` — an immutable, kernel-scoped execution-lifetime
  context (`configuration`, `logger`, `runtime`, `services`), the same
  shape as `tools.ToolContext` but subsystem-agnostic.
- `ExecutionResult` — a common, immutable outcome type
  (`success`, `payload`, `error`, `execution_time_seconds`, `metadata`),
  reusable as-is by future `workflow`/`agents` execution instead of each
  subsystem inventing its own.
- `Dispatcher` — routes a request to the Tool Runtime
  (`tools.ToolRegistry` + `tools.ToolExecutionPipeline`) or the Provider
  Runtime (`providers.ProviderRegistry`), translating each target's own
  result/exception shape into a common `ExecutionResult`. This is the only
  component in the subsystem that imports `tools` or `providers`.
- `ExecutionEngine` — the single orchestration entry point: logs the
  execution lifecycle and delegates dispatch selection to `Dispatcher`.

**Authorization and the event bus remain out of scope.** `ExecutionEngine`
performs no permission/authorization checks of its own — `ToolExecutionPipeline`
already enforces tool permissions given whatever `granted_permissions` its
caller supplies, and deciding *how* those permissions are granted is left,
as before, to a future subsystem. No event is published around dispatch;
`events` remains unimplemented and Execution Core does not anticipate its
shape.

**No concrete providers are added.** The Provider Runtime dispatch target
calls `BaseProvider.invoke` against whatever is already registered in
`ProviderRegistry` — it adds no new provider implementation, consistent
with `providers` remaining interfaces-only per Sprint 5.

## Alternatives considered

- **Fold orchestration into `tools` or `providers` directly** (e.g. give
  `ProviderRegistry` a `dispatch()` method mirroring `ToolExecutionPipeline`).
  Rejected: neither subsystem should depend on the other or on a shared
  request/result vocabulary; that dependency belongs in a layer above both,
  the same reasoning `docs/architecture.md` already gives for why
  `bootstrap` is a peer package rather than living inside `core`.
- **Wait until `workflow` or `agents` is built and let one of them own
  orchestration.** Rejected: both are explicitly named consumers of
  execution in ADR-0002's roadmap ordering, and building either first would
  force it to invent the shared request/result/context types this ADR
  fixes now, then retrofit `tools`/`providers` dispatch into them later.
- **Give `Dispatcher` a generic, pluggable target registry (e.g. register
  arbitrary `ExecutionTarget -> handler` mappings) instead of the two
  concrete targets named above.** Rejected as premature: only `tools` and
  `providers` have concrete runtimes to dispatch to today; a pluggable
  registry would be speculative surface for `workflow`/`agents` targets
  that do not exist yet, contrary to the kernel's "no placeholders for
  future features" principle.

## Consequences

- `tools` and `providers` remain unaware of `execution`; `execution`
  depends on both, keeping the dependency direction one-way, consistent
  with the acyclic subsystem graph described in `docs/architecture.md`.
- `workflow` and `agents`, when built, are expected to drive execution
  through `ExecutionEngine` rather than calling `ToolExecutionPipeline` or
  `BaseProvider.invoke` directly — this is now the kernel's single
  execution entry point.
- Any future dispatch target (a `workflow` step, an `agents` action)
  requires a deliberate extension of `Dispatcher` and, if warranted, a
  follow-up ADR — not silent accretion of new targets.
- `docs/architecture.md` and `docs/architecture/roadmap.md` are updated to
  reflect `execution` as a placed subsystem and to record that Sprint 6
  delivered Execution Core instead of the previously recommended event
  bus.
