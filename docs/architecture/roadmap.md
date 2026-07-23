# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

Status as of Sprint 6: Sprints 1–5 shipped `core`, `config`, `providers`
(interfaces only, no concrete implementation), `tools`, and `bootstrap`.
Sprint 6 shipped `execution` (Execution Core: `ExecutionRequest`,
`ExecutionContext`, `ExecutionResult`, `Dispatcher`, `ExecutionEngine`) —
see [ADR-0006](../adr/0006-execution-core-orchestration-layer.md) — instead
of the event bus originally recommended below for that slot. Sprint
sequencing is the user's to set, per the note under the original
recommendation; the event bus recommendation is carried forward into the
open slot it vacated rather than dropped. What follows is the approved
recommendation for the remaining sprints.

Recommendation, not a decision — architecture and sprint sequencing remain
the user's to set. Based on the dependency shape already visible in
ADR-0002's responsibility list: lower-dependency, higher-reuse subsystems
first, `agents`/`workflow` last since they're consumers of everything else.

| Sprint | Subsystem | Why this position |
|---|---|---|
| 6 | ~~Event bus (`events`)~~ → **Execution Core** (`execution`), shipped | Re-sequenced ahead of the event bus: `execution` implements ADR-0002's named-but-unplaced "AI orchestration" responsibility and gives `tools`/`providers` a shared dispatch entry point sooner, which later sprints (`agents`, `workflow`) can build on directly. |
| 7 | **Event bus** (`events`) | No dependencies beyond `core`; every later subsystem plausibly wants to publish/subscribe to lifecycle and state events, including around `execution`'s dispatch lifecycle. Also the natural backbone for future tracing/audit work. |
| 8 | **Memory abstraction** (`memory`) | No dependencies beyond `core`; needed by `agents` for state/context persistence. |
| 9 | **First concrete provider implementation** | Directly addresses the "unproven contract" limitation noted in `RELEASE_NOTES_v0.5.0.md` — proves `BaseProvider` against something real, dispatched through `execution`, before `agents` is built on top of it. Does not require a new subsystem package, just a first implementation inside `providers`. |
| 10 | **Plugin loading** (`plugins`) | No dependencies beyond `core`; benefits from `events` already existing (plugins commonly hook lifecycle events). Fills the one named-but-unimplemented capability sitting in an already-reserved package. |

**Beyond sprint 10 (not scheduled):** **Agent lifecycle** (`agents`,
depends on `providers`, `tools`, `execution`, `memory`, `events`), the
**workflow engine** (`workflow`, depends on `agents`/`tools`/`events` —
naturally last), **security primitives**, and the remainder of
**observability** (tracing, metrics, audit trail) — all still open per
ADR-0002, with no placement decided.
