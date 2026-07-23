# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

Status as of Sprint 7: Sprints 1–5 shipped `core`, `config`, `providers`
(interfaces only, no concrete implementation), `tools`, and `bootstrap`.
Sprint 6 shipped `execution` (Execution Core: `ExecutionRequest`,
`ExecutionContext`, `ExecutionResult`, `Dispatcher`, `ExecutionEngine`) —
see [ADR-0006](../adr/0006-execution-core-orchestration-layer.md) — instead
of the event bus originally recommended below for that slot. Sprint 7 was
**Integration Gate #1**: an unscheduled validation sprint (per
[CLAUDE.md](../../CLAUDE.md) §14) proving Execution Core end-to-end against
a bootstrapped runtime before further infrastructure was added — see
[`docs/reviews/sprint7-execution-core-integration-gate.md`](../reviews/sprint7-execution-core-integration-gate.md).
It shipped one additive API (`RuntimeContext.execution_context()`) and one
bugfix (a double-namespaced logger in `core.runtime.Kernel`), no new
subsystem. Sprint sequencing is the user's to set, per the note under the
original recommendation; the event bus recommendation is carried forward
into the open slot it vacated rather than dropped. What follows is the
approved recommendation for the remaining sprints.

Recommendation, not a decision — architecture and sprint sequencing remain
the user's to set. Based on the dependency shape already visible in
ADR-0002's responsibility list: lower-dependency, higher-reuse subsystems
first, `agents`/`workflow` last since they're consumers of everything else.

| Sprint | Subsystem | Why this position |
|---|---|---|
| 6 | ~~Event bus (`events`)~~ → **Execution Core** (`execution`), shipped | Re-sequenced ahead of the event bus: `execution` implements ADR-0002's named-but-unplaced "AI orchestration" responsibility and gives `tools`/`providers` a shared dispatch entry point sooner, which later sprints (`agents`, `workflow`) can build on directly. |
| 7 | **Integration Gate #1** — Execution Core validation, shipped | Inserted ahead of the event bus per CLAUDE.md §14: a newly implemented subsystem is validated end-to-end before more infrastructure is layered on top of it. Surfaced a real, if narrow, limitation — see the review's §3 — that later sprints (Authorization) need to account for. |
| 8 | **Event bus** (`events`) | No dependencies beyond `core`; every later subsystem plausibly wants to publish/subscribe to lifecycle and state events, including around `execution`'s dispatch lifecycle. Also the natural backbone for future tracing/audit work. |
| 9 | **Memory abstraction** (`memory`) | No dependencies beyond `core`; needed by `agents` for state/context persistence. |
| 10 | **First concrete provider implementation** | Directly addresses the "unproven contract" limitation noted in `RELEASE_NOTES_v0.5.0.md` — proves `BaseProvider` against something real, dispatched through `execution`, before `agents` is built on top of it. Does not require a new subsystem package, just a first implementation inside `providers`. |

**Beyond sprint 10 (not scheduled):** **Plugin loading** (`plugins`, no
dependencies beyond `core`, benefits from `events` already existing),
**Agent lifecycle** (`agents`, depends on `providers`, `tools`, `execution`,
`memory`, `events`), the **workflow engine** (`workflow`, depends on
`agents`/`tools`/`events` — naturally last), **security primitives**, an
**Authorization** subsystem (to close the permission-granting gap
Integration Gate #1 documented for `execution`), and the remainder of
**observability** (tracing, metrics, audit trail) — all still open per
ADR-0002, with no placement decided.
