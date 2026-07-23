# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

Status as of Sprint 13A: Sprints 1–5 shipped `core`, `config`, `providers`
(interfaces only, no concrete implementation), `tools`, and `bootstrap`.
Sprint 6 shipped `execution` (Execution Core) — see
[ADR-0006](../adr/0006-execution-core-orchestration-layer.md). Sprint 7 was
**Integration Gate #1**, an unscheduled validation sprint (per
[CLAUDE.md](../../CLAUDE.md) §14) that proved Execution Core end-to-end and
documented a real gap: no permissioned tool could be driven through
`ExecutionEngine` — see
[`docs/reviews/sprint7-execution-core-integration-gate.md`](../reviews/sprint7-execution-core-integration-gate.md).
Sprint 8 shipped `authorization` (`AuthorizationEngine`, `PermissionResolver`,
`PermissionSet`, `AuthorizationRequest`, `AuthorizationResult`) and closed
that gap by wiring an optional authorizer into `ExecutionEngine` — see
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md) —
again ahead of the event bus originally recommended for that slot. Sprint 9
shipped that event bus (`Event`, `EventBus`, `InMemoryEventBus`,
`EventHandler`, `EventRegistration`) and wired both `ExecutionEngine` and
`AuthorizationEngine` to publish lifecycle events through it — see
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md). Sprint 10
shipped the first concrete provider, `providers.claude.ClaudeProvider`
(Anthropic Messages API) — re-sequenced ahead of the memory abstraction
originally recommended for this slot, validating `BaseProvider`/
`execution`/`authorization` against a real LLM with no change to any of
the three; no ADR was needed there. Sprint 11 shipped that memory
abstraction (`Memory`, `MemoryStore`, `MemoryEntry`, `MemoryQuery`,
`MemoryResult`, `InMemoryStore`) — text memory only, no embeddings/vector/
RAG — and wired `ExecutionEngine` to optionally record execution outcomes
through it, with no dependency in either direction on any provider — see
[ADR-0009](../adr/0009-memory-subsystem-and-execution-recording.md). Sprint
12 shipped the workflow engine (`Workflow`, `WorkflowDefinition`,
`WorkflowStep`, `WorkflowContext`, `WorkflowEngine`, `WorkflowResult`) —
re-sequenced ahead of both plugin loading and agent lifecycle originally
recommended for slots 12–13, composing sequential `ExecutionEngine` calls
with no dependency back from `execution`/`authorization`/`memory`/`events`
— see
[ADR-0010](../adr/0010-workflow-engine-and-orchestration-boundary.md).
Sprint 13A shipped a first, deliberately minimal slice of `agents` — Agent
Runtime Core (`Agent`, `AgentDefinition`, `AgentContext`, `AgentEngine`,
`AgentResult`): an agent invokes exactly one workflow by delegating
entirely to `WorkflowEngine`, completing the chain
Agent → Workflow → Execution → Tool/Provider. No planning, reasoning,
reflection, or multi-agent composition yet — see
[ADR-0011](../adr/0011-agent-runtime-core-and-orchestration-chain.md).
What follows is the approved recommendation for the remaining sprints.

Recommendation, not a decision — architecture and sprint sequencing remain
the user's to set. Based on the dependency shape already visible in
ADR-0002's responsibility list: lower-dependency, higher-reuse subsystems
first, `agents`/`workflow` last since they're consumers of everything else.

| Sprint | Subsystem | Why this position |
|---|---|---|
| 6 | ~~Event bus (`events`)~~ → **Execution Core** (`execution`), shipped | Re-sequenced ahead of the event bus: `execution` implements ADR-0002's named-but-unplaced "AI orchestration" responsibility and gives `tools`/`providers` a shared dispatch entry point sooner, which later sprints (`agents`, `workflow`) can build on directly. |
| 7 | **Integration Gate #1** — Execution Core validation, shipped | Inserted ahead of the event bus per CLAUDE.md §14: a newly implemented subsystem is validated end-to-end before more infrastructure is layered on top of it. Surfaced a real, if narrow, limitation — see the review's §3 — that Sprint 8 (Authorization) closed. |
| 8 | ~~Event bus (`events`)~~ → **Authorization Engine** (`authorization`), shipped | Re-sequenced again, ahead of the event bus: closes the exact gap Integration Gate #1 documented, and places ADR-0002's named-but-unplaced "Security primitives" responsibility (partially — permission-based authorization only) before `agents`/`workflow` need to call anything permission-checked. |
| 9 | **Event bus** (`events`), shipped | No dependencies beyond `core`; every later subsystem plausibly wants to publish/subscribe to lifecycle and state events — `execution` and `authorization` both do so immediately. Also the natural backbone for future tracing/audit work. |
| 10 | ~~Memory abstraction (`memory`)~~ → **First concrete provider** (`providers.claude.ClaudeProvider`), shipped | Re-sequenced ahead of memory: validates `BaseProvider` against a real LLM (Anthropic) while the contract is still cheap to change if it had needed to be — before `agents`/`memory` are built assuming a shape that turned out wrong. It didn't need to change. |
| 11 | **Memory abstraction** (`memory`), shipped | No dependencies beyond `core`; needed by `agents` for state/context persistence, and now proven usable by `execution` for recording outcomes without any provider dependency in either direction. |
| 12 | ~~Plugin loading (`plugins`)~~ → **Workflow engine** (`workflow`), shipped | Re-sequenced ahead of plugin loading and agent lifecycle: composes `execution`/`memory`/`events` (all already shipped) into sequential multi-step runs, proving the orchestration/execution boundary (ADR-0010) before `agents` is built on top of either. |
| 13A | ~~Plugin loading (`plugins`)~~ → **Agent Runtime Core** (`agents`), shipped | Re-sequenced ahead of plugin loading again: a minimal, single-workflow agent runtime completes the orchestration chain (ADR-0011) while `workflow` is still fresh, before plugin loading (an unrelated, lower-priority capability) or richer agent behavior (planning, multi-agent) are attempted. |

**Beyond sprint 13A (not scheduled):** **Plugin loading** (`plugins`, no
dependencies beyond `core`, benefits from `events` already existing),
richer agent capabilities (planning, reasoning, reflection, multi-agent
composition, dynamic workflow selection — all deliberately deferred past
Sprint 13A), additional concrete providers (OpenAI, Gemini, Ollama —
explicitly out of scope for Sprint 10), a provider-side memory-consumption
mechanism (a provider reading prior memory as conversation context),
dynamic workflow steps (a step's request built from an earlier step's
result — deliberately not built in Sprint 12), parallel/scheduled workflow
execution, embeddings/vector search/RAG for `memory`, the remainder of
**Security primitives** (secrets management, encryption, audit trail), and
the remainder of **observability** (tracing, metrics, and building on top
of `events` for a trace/audit consumer) — all still open per ADR-0002,
with no placement decided.
