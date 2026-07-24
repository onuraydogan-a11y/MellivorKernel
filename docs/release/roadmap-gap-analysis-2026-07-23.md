# Mellivor Kernel — Roadmap Gap Analysis

Audit date: 2026-07-23
Audited commit: `7b115f7` (`docs(kernel): document observability foundation`)
Branch: `main`, matches `origin/main`
Version: `0.13.0` (release candidate, per `src/mellivor_kernel/version.py`)
Latest tag: `v0.5.0` → `138706e` (no tag exists for any release past `0.5.0`)

Scope: this is a read-only architecture/documentation audit. No code, tests,
or documentation were modified in producing this report.

Verification gates run during this audit, all green:

```text
pytest                 456 passed
ruff check .           All checks passed!
ruff format --check .  189 files already formatted
mypy                   Success: no issues found in 184 source files
```

(456 vs. the 447 recorded in `docs/release/release-audit.md` — the
difference is the 9 tests added by the security and observability
foundation sprints, both of which post-date that audit; see §4.)

---

## 1. Completed roadmap items

Per `docs/architecture/roadmap.md` and the ADR index, the following are
implemented, documented, and tested:

| # | Subsystem | Package | ADR | Notes |
|---|---|---|---|---|
| 1–5 | `core`, `config`, `providers` (interface), `tools`, `bootstrap` | shipped Sprints 1–5 | — | Foundation layer; `RELEASE_NOTES_v0.5.0.md` is the historical record |
| 6 | Execution Core | `execution` | ADR-0006 | Orchestration layer; dispatches to tools/providers |
| 7 | Integration Gate #1 | — | — | Validation sprint, not a subsystem; documented the authorization gap closed by Sprint 8 |
| 8 | Authorization Engine | `authorization` | ADR-0007 | Decoupled from `execution` via a structural `Authorizer` protocol |
| 9 | Event Bus | `events` | ADR-0008 | In-process pub/sub; `execution`/`authorization` publish lifecycle events |
| 10 | Claude Provider | `providers.claude` | — (no ADR needed) | First concrete provider, validates `BaseProvider` against a real LLM |
| 11 | Memory abstraction | `memory` | ADR-0009 | Text-only, in-memory; `execution` optionally records outcomes |
| 12 | Workflow Engine | `workflow` | ADR-0010 | Sequential composition of `ExecutionEngine` calls |
| 13A | Agent Runtime Core | `agents` | ADR-0011 | One agent → one workflow, no planning/reasoning |
| 14 | Integration Gate #2 | — | — | Release audit at `548a95a`, approved v0.13.0 RC scope |
| — | Security foundation | `security` | ADR-0012 | Contracts-only: `Secret`, `SecretProvider(Registry)`, `SecurityPolicy`, `SecurityDecision`, `SecureConfiguration`, `AuditRecord`/`AuditSink`, exceptions |
| — | Observability foundation | `observability` | ADR-0013 | Contracts-only: `ObservationContext`, `MetricsRecorder`, `TraceRecorder`/`TraceSpan`, `StructuredEventSink`/`Event`, no-op defaults, `Observability` DI wrapper |

All 12 packages under `src/mellivor_kernel/` import cleanly with an acyclic
dependency graph (last confirmed in the Sprint 14 audit; re-verified here —
no new cross-package imports were introduced by the security/observability
sprints, which both remain dependency-injected leaves off `core` only).

Every implemented subsystem has: an ADR (where architecturally significant),
a `docs/specs/*.md` entry, a `tests/<subsystem>/` suite, and — for
subsystems through Sprint 13A — a runnable example in `examples/`.

---

## 2. Partially completed items

These have a real but intentionally narrow slice implemented; the roadmap
and specs already document the narrowing, so these are not surprises, but
they are not "done" against ADR-0002's full responsibility list:

- **Security primitives** (`security`, ADR-0012) — contracts and
  abstractions only (secret holding/masking, a resolve-by-name registry, a
  structural policy protocol, audit record/sink protocols). No concrete
  `SecretProvider` implementation (e.g. env-backed, vault-backed), no
  authentication/OAuth/SSO/RBAC, no encryption. Explicitly out of scope per
  the ADR. **Not yet consumed anywhere** — see §4.
- **Observability** (`observability`, ADR-0013) — contracts, correlation-ID
  support, and no-op implementations only. No metrics backend, no tracing
  vendor integration, no exporter. Structured logging (`core/logging.py`,
  Sprint 2) remains the only observability capability actually wired into
  a running subsystem. **Not yet consumed anywhere** — see §4.
- **Agent Runtime** (`agents`) — a single agent delegates to exactly one
  workflow. No planning, reasoning, reflection, dynamic workflow selection,
  or multi-agent composition.
- **Workflow Engine** (`workflow`) — sequential only. No dynamic steps
  (a step's request built from a prior step's result), no parallel or
  scheduled execution.
- **Memory** (`memory`) — text-only, in-memory (`InMemoryStore`). No
  persistence, embeddings, vector search, or RAG. No provider-side
  memory-consumption mechanism (a provider reading prior memory as
  conversation context).
- **Multi-LLM provider abstraction** (`providers`) — interface plus exactly
  one concrete implementation (`ClaudeProvider`). OpenAI, Gemini, and
  local-model integrations are explicitly out of scope so far.
- **Bootstrap composition** (`bootstrap`) — composes `config` + `core` +
  `providers` + `tools` only. `ExecutionEngine`, `AuthorizationEngine`,
  `WorkflowEngine`, `AgentEngine` — and now `security`/`observability` — are
  not wired in; every consumer (including all four `examples/`) composes
  them by hand. This is documented as deliberate, not a defect, but it is a
  growing pile of manual wiring as more engines ship.

---

## 3. Missing items

Per ADR-0002's fixed responsibility list and the roadmap's "beyond Sprint
13A" section, still entirely unaddressed:

- **Plugin loading** (`plugins`) — package exists as an empty skeleton
  (`src/mellivor_kernel/plugins/__init__.py` is a zero-byte file with no
  docstring, exports, or content). No discovery, registration, or lifecycle
  mechanism of any kind. No spec, no ADR, no tests, no example.
- **Secrets management / encryption** as concrete capabilities (only the
  `security` foundation's abstractions exist — see §2).
- **Distributed/durable event delivery** — `events` is in-process only; no
  ADR has yet decided whether distributed delivery is in or out of v1.0
  scope (flagged as open in the v1.0 checklist).
- **A published `CHANGELOG.md`** — ADR-0005 §"Consequences" commits to
  "every MAJOR and MINOR release is documented with a changelog." Only one
  historical document exists, `RELEASE_NOTES_v0.5.0.md`, covering the
  `0.5.0` release. Seven MINOR releases have shipped since (`0.6.0` through
  `0.13.0`, one per subsystem sprint) with no corresponding changelog
  entries — the roadmap document is a narrative substitute, not a changelog.
- **Release tags past `v0.5.0`** — `version.py` is at `0.13.0`, but `git
  tag` shows only `v0.5.0`. No tag exists for any of the seven MINOR bumps
  that followed. (May be intentional while still pre-1.0/RC — flagged for a
  decision, not asserted as a defect.)

---

## 4. Architecture inconsistencies

These are the audit's primary findings — places where the documentation
set no longer agrees with the actual repository state, in direct tension
with CLAUDE.md §7 ("Whenever architecture changes, update all affected
documents in the same sprint. Never leave documentation stale.").

1. **`docs/architecture/roadmap.md` does not mention Sprint 14 or the
   security/observability sprints at all.** Its "Status as of Sprint 13A"
   narrative and sprint table stop at Agent Runtime Core, and its "Beyond
   sprint 13A (not scheduled)" paragraph still lists "the remainder of
   Security primitives" and "the remainder of observability" as unscheduled
   future work — even though ADR-0012 and ADR-0013 (both dated 2026-07-23,
   both `Accepted`, both with shipped code and passing tests) have already
   placed and partially filled both. The roadmap has not been updated
   since Sprint 13A shipped.
2. **`docs/architecture.md`'s status line and both "Partially placed"
   sections are stale in the same way.** Line 3 still reads "Security
   primitives and most of Observability remain unaddressed," and the
   subsystem diagram/list has no entry for `security` or `observability` as
   packages, even though both now exist under `src/mellivor_kernel/` with
   accepted ADRs and specs. The document was last updated for Sprint 13A
   and was not revisited for the two sprints after it.
3. **`docs/release/release-audit.md` (Sprint 14 / Integration Gate #2) is
   now stale relative to `main`.** It was authored and committed
   (`a10a7bf`) immediately after the audited commit `548a95a`, but the
   security and observability foundations shipped in the *next* two commits
   after that (`74f9597`/`f8d2965`, `e6b36ec`/`7b115f7`) and were never
   folded back into the audit doc. Its "Release Risks" section still lists
   "Security primitives beyond authorization... remain unaddressed" and
   "Observability beyond structured logging... remains unaddressed" as flat
   statements, and its test count (447) undercounts the current suite (456)
   by exactly the tests those two sprints added. This isn't a defect in the
   audit as written — it was accurate at the time — but it is now
   presented as the current release-readiness record without a note that
   two sprints have since landed.
4. **`docs/release/v1.0-release-checklist.md`'s responsibility table has
   the same staleness.** The "Security primitives" and "Observability"
   rows describe only the pre-ADR-0012/0013 state ("Authorization is
   implemented as a partial slice... Secrets management, encryption, and
   audit trail remain unaddressed" / "Structured logging is implemented.
   Tracing, metrics, and audit trail remain unaddressed"). Both rows need
   an update to reflect that foundation-level contracts now exist, even
   though the substantive gap (no concrete secret provider, no metrics/
   tracing backend) is real and should stay flagged.
5. **`README.md`'s "Status" section and repository layout are stale for
   the same two sprints.** "Security primitives and most of Observability
   remain unaddressed" (line 133–134) and the "Implemented so far" list
   enumerates every subsystem through `agents` but never mentions `security`
   or `observability`; the repository-layout code block (lines 74–86) lists
   `authorization` but not `security` or `observability` as directories
   under `src/mellivor_kernel/`.
6. **`docs/specs/README.md`'s index is missing two entries.**
   `docs/specs/security.md` and `docs/specs/observability.md` both exist,
   are well-formed, and are linked *from* their respective ADRs, but the
   spec directory's own index (lines 10–22) was never updated to list them
   — the index still ends at `agents.md`.
7. **No architecture-level ADR or diagram places `security`/
   `observability` in the subsystem dependency diagram.** ADR-0012/0013
   both describe the two packages as "structurally separate" and
   dependency-injected, but neither `docs/architecture.md`'s ASCII diagram
   nor the Sprint 14 audit's dependency-graph listing (`agents -> core,
   events, memory, workflow`, etc.) has been extended to include them. A
   reader relying on that diagram would not know the two packages exist.

None of these are contract-breaking or functionally incorrect — the code
itself is internally consistent, acyclic, and fully tested. The
inconsistency is entirely in the five-plus documents that are supposed to
track it, which is itself notable given CLAUDE.md's explicit "never leave
documentation stale" instruction and the fact that the two sprints in
question both *did* produce their own ADR and spec — the omission is
specifically in the cross-cutting summary documents (roadmap, architecture
overview, release audit, checklist, README, specs index) that sit above
individual subsystem docs.

---

## 5. Technical debt

- **`security` and `observability` have zero internal consumers.** Neither
  package is imported by `execution`, `workflow`, `agents`, `bootstrap`, or
  any file under `examples/`. This is consistent with ADR-0012/0013's
  "dependency-injected, structurally separate" design intent, but it puts
  both packages in tension with CLAUDE.md §13 ("Dogfood Principle: No
  public SDK or extension point is finalized before internal usage proves
  the design"). As written, both subsystems' public contracts have only
  been exercised by their own foundation tests
  (`tests/security/test_foundation.py`, 102 lines;
  `tests/observability/test_foundation.py`, 55 lines), never by a real
  kernel code path. There is a real risk the contracts (e.g. `SecretProvider
  .resolve`, `MetricsRecorder.increment`, `TraceRecorder.start_span`) turn
  out to be the wrong shape once something actually depends on them,
  exactly the failure mode the dogfood principle exists to catch — as
  happened productively in Sprint 7 (Integration Gate #1 surfaced a real
  `execution`/`authorization` gap this way).
- **Manual bootstrap wiring is growing linearly with each sprint.**
  `BootstrapBuilder`/`KernelBootstrap` compose four subsystems automatically
  and leave six more (`execution`, `authorization`, `workflow`, `agents`,
  and now `security`, `observability`) for every consumer to wire by hand.
  Each of the four `examples/` files re-derives a similar manual
  composition. This is documented as deliberate per-sprint, but nothing in
  the roadmap addresses when (or whether) bootstrap should absorb any of
  this — it is accumulating without a stated resolution point.
  `docs/release/v1.0-release-checklist.md` flags "Bootstrap does not
  automatically compose the newer engines" as a current limitation but does
  not assign it an owner or a decision deadline.
- **No changelog mechanism exists despite ADR-0005 committing to one.**
  Every MINOR release since `0.5.0` (seven of them) has no changelog entry;
  the roadmap document is being used as a de facto substitute, but it's
  prose describing sprint rationale, not a version-keyed changelog a
  consumer could diff against. This will get harder to retrofit the longer
  it's deferred.
- **No release tag has been cut since `v0.5.0`**, even though
  `version.py` has moved through 0.6.0–0.13.0. If this is intentional
  (e.g., tags reserved for `1.0.0` and later), it should be stated
  somewhere (ADR-0005 is silent on tag *cadence*, only on version
  *semantics*); if not intentional, seven releases' worth of tags are
  missing.
- **`design/` directory is empty** (present in the working tree but
  untracked/contentless — Git does not track empty directories, so it
  currently holds nothing). Not urgent, but worth confirming it is meant to
  be a live design-artifact directory rather than leftover scaffolding, since
  nothing references it from any doc.
- **`plugins/__init__.py` is a literal zero-byte file** — no docstring
  explaining *why* it's intentionally empty. Every other unimplemented-but-
  reserved package in this codebase (there are none, since `plugins` is the
  only one) — but if another reserved-but-empty package is ever added, a
  one-line docstring pointing at the roadmap/ADR-0002 placement would save
  a reader from wondering whether the file is an oversight versus a
  deliberate placeholder. Currently only discoverable by cross-referencing
  the README/roadmap.

---

## 6. Recommended next sprint

Two candidate sprints compete for next slot; recommend splitting them
rather than picking one, since one is docs-only and cheap, the other is
implementation:

**Sprint 16a — Documentation reconciliation (do first, do fast).**
Not a feature sprint; closes the gaps in §4 before another feature sprint
makes the drift worse. Concretely:
- Add Sprint 14/15/16 entries to `docs/architecture/roadmap.md` covering
  Integration Gate #2, the security foundation, and the observability
  foundation, and remove both from the "beyond Sprint 13A, not scheduled"
  paragraph.
- Update `docs/architecture.md`'s status line, subsystem list, and diagram
  to include `security` and `observability`.
- Add `security.md` and `observability.md` to `docs/specs/README.md`'s
  index.
- Update `README.md`'s Status section and repository-layout block.
- Add an explicit "superseded by Sprints 14/15" style note (not a rewrite —
  CLAUDE.md's no-deletion rule and ADR history norms both apply) to
  `docs/release/release-audit.md` and refresh the responsibility table in
  `docs/release/v1.0-release-checklist.md`.

This sprint is small, low-risk, and directly required by CLAUDE.md §7; it
should not be skipped in favor of jumping straight to new features.

**Sprint 16b — Dogfood the security and observability foundations.**
Per CLAUDE.md §13, neither foundation should be considered final until
something in the kernel actually depends on it. The lowest-risk, highest-
signal candidate: wire `observability.ObservationContext` /
`StructuredEventSink` through `execution.ExecutionEngine` alongside the
existing `events.EventBus` publication added in Sprint 9 — `execution`
already publishes lifecycle events, so adding a parallel, optional
structured-observation emission exercises the new contracts against a real
call path without touching `workflow`/`agents`/`providers`. This sprint
would likely surface whether `MetricsRecorder`/`TraceRecorder`'s shape is
right before more code depends on it, the same value Sprint 7's Integration
Gate delivered for `execution`/`authorization`. Follow with an equivalent
`security.AuditSink` wiring into `authorization.AuthorizationEngine`'s
existing grant/deny decision path, since that engine already produces
exactly the subject/action/decision triple `AuditRecord` is shaped for.

Recommend running 16a and 16b as separate commits (matching CLAUDE.md §10's
"one sprint = one feature commit," with docs corrections kept out of the
feature commit), with 16a landing first since it's a prerequisite for an
accurate roadmap going into 16b.

**Not recommended next:** plugin loading. It remains the largest fully-
unaddressed responsibility, but every re-sequencing decision from Sprint 6
onward has deliberately deferred it in favor of subsystems the rest of the
kernel could immediately build on — that reasoning still applies, since
nothing yet consumes `security`/`observability` either. Reconsider after
16b closes the dogfooding gap.
