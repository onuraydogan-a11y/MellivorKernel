# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

Status as of v0.5.0: Sprints 1–5 shipped `core`, `config`, `providers`
(interfaces only, no concrete implementation), `tools`, and `bootstrap`.
What follows is the approved recommendation for sprints 6–10.

Recommendation, not a decision — architecture and sprint sequencing remain
the user's to set. Based on the dependency shape already visible in
ADR-0002's responsibility list: lower-dependency, higher-reuse subsystems
first, `agents`/`workflow` last since they're consumers of everything else.

| Sprint | Subsystem | Why this position |
|---|---|---|
| 6 | **Event bus** (`events`) | No dependencies beyond `core`; every later subsystem plausibly wants to publish/subscribe to lifecycle and state events. Also the natural backbone for future tracing/audit work. |
| 7 | **Memory abstraction** (`memory`) | No dependencies beyond `core`; needed by `agents` for state/context persistence. |
| 8 | **First concrete provider implementation** | Directly addresses the "unproven contract" limitation noted in `RELEASE_NOTES_v0.5.0.md` — proves `BaseProvider` against something real before `agents` is built on top of it. Does not require a new subsystem package, just a first implementation inside `providers`. |
| 9 | **Plugin loading** (`plugins`) | No dependencies beyond `core`; benefits from `events` already existing (plugins commonly hook lifecycle events). Fills the one named-but-unimplemented capability sitting in an already-reserved package. |
| 10 | **Agent lifecycle** (`agents`) | Depends on `providers`, `tools`, `memory`, `events` — the first subsystem that is a genuine consumer of everything built above. |

**Beyond sprint 10 (not scheduled):** the **workflow engine** (`workflow`,
depends on `agents`/`tools`/`events` — naturally last), **security
primitives**, and the remainder of **observability** (tracing, metrics,
audit trail) — all still open per ADR-0002, with no placement decided.
