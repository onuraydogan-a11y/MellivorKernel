# 0019. Release Readiness & Scope Lock

Status: Accepted
Date: 2026-07-27

## Context

[ADR-0005](0005-versioning-strategy.md) fixed the condition for `1.0.0`
from the start: "The kernel moves to `1.0.0` only once the subsystem
contracts for the full responsibility list in
[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) are
considered stable, a decision to be made explicitly via a future ADR,
not declared unilaterally by a release." Twenty-three sprints have since
built at least a foundation for every one of ADR-0002's eleven named
responsibilities — the last gap, provider coverage, closed in Sprint 23
— but that future ADR has never been written. `docs/release/v1.0-release-
checklist.md` has instead accumulated eleven open rows, nine of them
phrased as an undecided question ("Decide...", "Confirm...", "Define...")
rather than a stated implementation gap, and its own "Release gate"
section names the missing decision explicitly: *"The release decision is
recorded in an ADR or other approved release decision."*

Sprint 24's own planning gate concluded that resolving this ambiguity —
not implementing any further capability — is the highest-value next
step: every candidate sprint considered (a concrete security backend, a
concrete observability backend, richer agent capability, workflow
dynamic steps, memory persistence, additional providers) is currently
unscopable, because none of the responsibility rows that would justify
or exclude them has ever been decided. Building any of them first risks
building the wrong size of thing — the release checklist's own language
("Define placement **and** implement") already says the decision comes
first.

**What this ADR is, and is not.** This is the scope-defining decision
ADR-0005 anticipates — it establishes, per responsibility, what "stable
enough for `1.0.0`" means and whether that bar is already met, met by a
small closing action, or explicitly not required until later. It is
**not** the final "declare `1.0.0` now" release ADR itself: several
responsibilities below are `Included in v1.0` but still have a small,
named closing action outstanding (see each entry). Declaring `1.0.0`
remains a separate, later decision, made once every `Included in v1.0`
item's closing action is actually done.

## Decision

Every one of ADR-0002's eleven kernel responsibilities is classified
into exactly one of three buckets:

- **Included in v1.0** — required for the `1.0.0` compatibility promise.
  Either already satisfied as-is (no code change needed, only a formal
  confirmation), or satisfied pending one small, already-scoped closing
  action.
- **Deferred to v1.1** — a real, understood, boundable capability
  expansion. Not required to cross the `1.0.0` line, but scoped enough
  to schedule directly once `1.0.0` ships, with no further design gate
  needed first.
- **Future research** — genuinely open-ended. No committed design, no
  stated timeline, and in several cases an open question about whether
  the capability belongs in the kernel at all (per
  [ADR-0003](0003-repository-boundaries.md)'s infrastructure/business-
  application boundary) rather than in a consuming product. Requires its
  own future planning gate — possibly its own Architecture Challenge —
  before it can be scheduled at all.

| # | Responsibility | Classification | Rationale |
|---|---|---|---|
| 1 | **AI orchestration** (`execution`) | **Included in v1.0** — satisfied | The most exercised contract in the kernel: every other subsystem (`tools`, `providers`, `authorization`, `workflow`, `agents`, `ai_engine`) depends on `ExecutionEngine`/`Dispatcher`, across 23 sprints, with zero contract changes ever required. Closing action: none — formally ratified stable by this ADR. |
| 2 | **Agent lifecycle** (`agents`) | Split: baseline **Included in v1.0** — satisfied; richer capability **Future research** | The current, deliberately minimal contract (one agent invokes exactly one workflow, per [ADR-0011](0011-agent-runtime-core-and-orchestration-chain.md)) is stable and is what `1.0.0`'s compatibility promise covers. Planning, reasoning, reflection, and multi-agent composition remain unscoped and are not promised by `1.0.0` — attempting to scope them now, before `1.0.0` ships, risks exactly the "opinionated AI framework" drift ADR-0002 fences the kernel away from. |
| 3 | **Workflow engine** (`workflow`) | Split: sequential execution **Included in v1.0** — satisfied; dynamic/parallel/scheduled execution **Deferred to v1.1** | Sequential `WorkflowEngine` is stable and proven through `agents`/`ai_engine`. Dynamic steps (a step's request built from an earlier step's result), parallel execution, and scheduling are well-understood, boundable extensions — unlike agent planning, their shape is already reasonably clear from [ADR-0010](0010-workflow-engine-and-orchestration-boundary.md)'s own deferral language — so they can be scheduled directly post-`1.0.0` without another design gate. |
| 4 | **Memory abstraction** (`memory`) | Split: text/in-memory **Included in v1.0** — satisfied; persistence **Deferred to v1.1**; embeddings/vector/RAG **Future research** | `InMemoryStore` text memory is stable and proven via `execution`/`agents` recording. A second, persistent `MemoryStore` implementation is the same well-precedented "second concrete implementation proves the abstraction" pattern Sprint 10 and Sprint 23 already used for `providers` — scoped, low-risk, schedulable directly. Embeddings/vector search/RAG bundle unresolved, provider-coupled design questions (which embedding contract, which vector store, how it interacts with `providers`) with no design started. |
| 5 | **Tool execution** (`tools`) | **Included in v1.0** — satisfied | Mature since Sprint 3/4; every execution path in the kernel flows through `ToolRegistry`/`ToolExecutionPipeline`. No known gap. Closing action: none. |
| 6 | **Event bus** (`events`) | Split: in-process bus **Included in v1.0** — satisfied; distributed delivery **Future research** | `InMemoryEventBus` is stable and sufficient for the kernel's own internal lifecycle events. [ADR-0008](0008-event-bus-and-lifecycle-events.md) already designed `EventBus` so a distributed implementation is a drop-in replacement requiring no change to `ExecutionEngine`/`AuthorizationEngine` — but no concrete distributed backend has been designed, requested, or scoped, so it stays open-ended rather than scheduled. |
| 7 | **Plugin loading** (`plugins`, `plugin_sdk`, `plugins_builtin`, `plugin_discovery`) | Split: runtime+SDK+discovery+one built-in plugin **Included in v1.0** — satisfied; marketplace/remote plugins/sandboxing/hot reload/signature verification/package installation **Future research** | The runtime, SDK, filesystem discovery, and one built-in plugin are proven twice over (Sprints 20 and 21). Every excluded item was already explicitly deferred, individually, across [ADR-0014](0014-plugin-runtime-foundation.md)/[0016](0016-system-info-built-in-plugin.md)/[0017](0017-plugin-discovery-foundation.md) as "a meaningfully larger, separate concern." Sandboxing and signature verification are security-critical and unscoped; a marketplace and remote-plugin execution are arguably closer to a product/ecosystem concern than a kernel primitive at all, per ADR-0003's infrastructure/business-application boundary, and have no committed design. |
| 8 | **Multi-LLM provider abstraction** (`providers`) | Split: `BaseProvider` contract + `ClaudeProvider` + `OpenAIProvider` **Included in v1.0** — satisfied; additional providers **Deferred to v1.1** | The abstraction is now proven twice, against genuinely different vendor shapes (Sprint 10, Sprint 23) — the strongest possible evidence it generalizes. Additional concrete providers (Gemini, local models) are the same well-precedented, scoped, low-risk pattern and can be added directly without a further design gate. **Closing action resolved in Sprint 25:** the four-way exception granularity is ratified as-is as the intentional, required error-model shape for any provider, and `ProviderCapabilities`'s current all-`False` values are ratified as accurate (not aspirational) for both existing providers. Both decisions required no code change — see the "v1.0 contract ratification" section of [`docs/specs/providers.md`](../specs/providers.md). This responsibility now carries no open closing action. |
| 9 | **Configuration** (`config`) | **Included in v1.0** — satisfied | Unchanged since Sprint 2; every subsystem depends on it. No known gap. Closing action: none. |
| 10 | **Observability** (`observability`) | Split: structured logging + contracts foundation + first consumer (`execution`) **Included in v1.0** — satisfied as "bring your own backend"; concrete metrics/tracing vendor integration **Future research** | Structured logging plus the Sprint 16 contracts-and-no-ops foundation plus Sprint 17's wiring into `execution` together form a legitimate, honest `1.0.0` story: the kernel exposes a pluggable observation contract and emits through it, without committing to a vendor. A concrete metrics/tracing backend is a real vendor-integration decision (which platform, whose infrastructure) with no committed direction, so it stays open rather than scheduled. |
| 11 | **Security primitives** (`security`, `authorization`) | Split: permission-based `authorization` + `security` contracts foundation + audit wiring **Included in v1.0** — satisfied as "bring your own backend"; concrete `SecretProvider` backend **Deferred to v1.1**; authentication/OAuth/SSO/RBAC/encryption-at-rest **Future research** | `authorization`'s permission model is mature and dogfooded everywhere; the `security` foundation's contracts plus Sprint 17's `AuditSink` wiring give the same honest "hook exists, bring your own backend" story as observability. A concrete `SecretProvider` backend is the same scoped, low-risk, "second concrete implementation" pattern already proven for `providers` and `memory`. Authentication, OAuth, SSO, RBAC, and encryption-at-rest are not just unscoped — they raise a genuine, unresolved question of whether they belong in the kernel at all versus in a consuming product's own identity layer, per ADR-0003; that question needs its own future Architecture Challenge before any of it can be scheduled. |

`ai_engine` is not a named ADR-0002 responsibility and needs no entry
here — per [ADR-0018](0018-ai-engine-foundation.md), it composes
responsibilities that already exist rather than adding one, and this
scope lock does not change that.

## Alternatives considered

- **Implement one of the deferred/future-research candidates directly
  instead of writing this ADR.** Rejected: every such candidate's own
  release-checklist row requires a decision before (or alongside) an
  implementation, and several — richer agent capability chief among them
  — risk being built at the wrong scope, or built at all, without this
  decision existing first.
- **Declare `1.0.0` now, treating every "Included" item as already
  closed.** Rejected: several `Included in v1.0` responsibilities carry
  a small, explicitly named closing action (the provider exception-
  granularity/`ProviderCapabilities` question chief among them) that
  hasn't been done yet. Declaring `1.0.0` before those close would
  freeze a contract this ADR itself flags as still open.
- **Leave the release checklist's open questions unresolved and continue
  choosing sprints ad hoc.** Rejected: three consecutive planning gates
  (Sprints 21, 23, 24) each re-derived "what's next" from first
  principles with no fixed target to converge toward. This ADR exists
  specifically to stop that recurrence.

## Consequences

- Every future sprint proposal can be evaluated against this
  classification directly: an `Included in v1.0` closing action is
  release-blocking; a `Deferred to v1.1` item is schedulable any time
  after `1.0.0` without a further design gate; a `Future research` item
  requires its own planning/Architecture Challenge before it can be
  scheduled at all.
- `docs/release/v1.0-release-checklist.md` is updated in the same sprint
  to reflect this classification per responsibility, replacing its
  eleven previously-open rows.
- `docs/architecture/roadmap.md` is updated in the same sprint to record
  Sprints 21–23 (omitted from it at the time, per those sprints' own
  explicit instructions) and to restate its "not scheduled" backlog in
  terms of this ADR's three buckets.
- `1.0.0` is not declared by this ADR. It is declared by a later,
  separate decision, once every `Included in v1.0` responsibility's
  named closing action is actually complete.
- This classification is a decision, not an implementation commitment:
  no code, test, or configuration changes accompany this ADR.
- **Sprint 25 update:** the one outstanding closing action (responsibility
  #8, provider exception granularity and `ProviderCapabilities`) is
  resolved, as-is, with no code change. Every `Included in v1.0`
  responsibility now carries no open closing action.
