# 0020. Release Decision: Mellivor Kernel v1.0.0

Status: Accepted
Date: 2026-07-28

## Context

[ADR-0005](0005-versioning-strategy.md) fixed the condition for `1.0.0` from
the start: the kernel moves to `1.0.0` only once the subsystem contracts for
the full responsibility list in [ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md)
are considered stable, "a decision to be made explicitly via a future ADR,
not declared unilaterally by a release." [ADR-0019](0019-release-readiness-and-scope-lock.md)
(Sprint 24) resolved the scope ambiguity that condition depended on,
classifying every one of ADR-0002's eleven responsibilities as `Included in
v1.0`, `Deferred to v1.1`, or `Future research` — but ADR-0019 explicitly
declined to be that future ADR itself: "`1.0.0` is not declared by this
ADR... it is declared by a later, separate decision, once every `Included in
v1.0` responsibility's named closing action is actually complete."

Sprint 25 resolved the one closing action ADR-0019 left open (provider
exception granularity and `ProviderCapabilities`, ratified with no code
change) and approved the public API/compatibility policy through the Public
API Freeze Audit. Sprint 26 closed the two remaining items in
`docs/release/v1.0-release-checklist.md`'s "Release gate" section: a full
test/lint/format/strict-mypy verification run recorded against the release
candidate, and a documentation/examples parity confirmation (one drift item
found and corrected in `docs/specs/observability.md`). As of this ADR, all
five "Release gate" items are checked and no `Included in v1.0`
responsibility carries an open closing action. The future ADR ADR-0005
anticipated has never been written until now.

## Decision

Mellivor Kernel is declared `1.0.0`, effective at the commit that
accompanies this ADR (`src/mellivor_kernel/version.py` bumped from `0.13.0`
to `1.0.0` in the same change).

The scope of the `1.0.0` compatibility promise is exactly ADR-0019's
per-responsibility classification, restated here so it is readable from
this decision alone:

| # | Responsibility | v1.0.0 covers | Explicitly not covered |
|---|---|---|---|
| 1 | AI orchestration (`execution`) | Full contract — satisfied, no gap | — |
| 2 | Agent lifecycle (`agents`) | Baseline: one agent invokes exactly one workflow | Planning, reasoning, reflection, multi-agent composition (`Future research`) |
| 3 | Workflow engine (`workflow`) | Sequential execution | Dynamic steps, parallel execution, scheduling (`Deferred to v1.1`) |
| 4 | Memory abstraction (`memory`) | Text/in-memory (`InMemoryStore`) | Persistence (`Deferred to v1.1`); embeddings/vector/RAG (`Future research`) |
| 5 | Tool execution (`tools`) | Full contract — satisfied, no gap | — |
| 6 | Event bus (`events`) | In-process bus (`InMemoryEventBus`) | Distributed delivery (`Future research`) |
| 7 | Plugin loading (`plugins`, `plugin_sdk`, `plugins_builtin`, `plugin_discovery`) | Runtime, SDK, filesystem discovery, one built-in plugin | Marketplace, remote plugins, sandboxing, hot reload, signature verification, package installation (`Future research`) |
| 8 | Multi-LLM provider abstraction (`providers`) | `BaseProvider` contract, `ClaudeProvider`, `OpenAIProvider` | Additional providers (Gemini, local models) (`Deferred to v1.1`) |
| 9 | Configuration (`config`) | Full contract — satisfied, no gap | — |
| 10 | Observability (`observability`) | Structured logging, contracts foundation, `execution` wiring — "bring your own backend" | Concrete metrics/tracing vendor integration (`Future research`) |
| 11 | Security primitives (`authorization`, `security`) | Permission-based authorization, security/audit contracts, audit wiring — "bring your own backend" | Concrete `SecretProvider` backend (`Deferred to v1.1`); authentication, OAuth, SSO, RBAC, encryption-at-rest (`Future research`) |

From this commit forward:

- ADR-0005's post-1.0 SemVer discipline is binding: a breaking change to any
  public contract requires a MAJOR version bump; a backward-compatible
  addition requires a MINOR bump; a backward-compatible fix requires only a
  PATCH bump.
- ADR-0005's deprecation policy is now in effect: a public contract element
  slated for removal must first be marked deprecated in a MINOR release,
  with a documented migration path, and may not be removed before the next
  MAJOR release.
- The public API surface ratified by the Sprint 25 Public API Freeze Audit
  constitutes the `1.0.0` compatibility promise.
- `Deferred to v1.1` and `Future research` items remain exactly as
  classified by ADR-0019. This ADR schedules none of them and expands none
  of their scope.

## Alternatives considered

- **Declare `1.0.0` before Sprint 26 closed the Release Gate.** Rejected:
  two of the five "Release gate" checklist items — the recorded verification
  run and the documentation/examples parity confirmation — were still open
  at that point. Declaring `1.0.0` before they closed would have frozen a
  compatibility promise the checklist itself flagged as unverified.
- **Wait for a `Deferred to v1.1` item (e.g. a persistent `MemoryStore`, a
  concrete `SecretProvider` backend, an additional provider) before
  declaring `1.0.0`.** Rejected: ADR-0019 already classified each of these
  as explicitly not required for `1.0.0`. Waiting for any of them would
  contradict that scope lock and indefinitely defer a decision every
  precondition already satisfies.
- **Continue operating pre-1.0 (`0.y.z`) indefinitely rather than declaring.**
  Rejected: ADR-0005's pre-1.0 convention (breaking changes permitted in
  MINOR releases) was always meant to be temporary, for as long as the
  kernel's contracts were still being established. Every condition ADR-0005
  set for ending that period is now met.

## Consequences

- `src/mellivor_kernel/version.py` moves from `0.13.0` to `1.0.0` in the
  same change as this ADR.
- `CHANGELOG.md` and `RELEASE_NOTES_v1.0.0.md` are added to record the
  release.
- `README.md`, `docs/architecture.md`, and
  `docs/release/v1.0-release-checklist.md` are updated in the same change
  to reflect `1.0.0` status and reference this ADR; `docs/adr/README.md`'s
  index is updated to list it.
- Tagging `v1.0.0` and creating the corresponding GitHub Release are
  deliberately separate, later, manual actions — not performed by this ADR
  or the commit that accompanies it.
- Every subsequent breaking change to a documented public contract now
  requires its own ADR and a MAJOR version bump, per ADR-0005 — this ADR is
  the point from which that discipline is binding, not merely aspirational.
- This decision does not implement, schedule, or expand the scope of any
  `Deferred to v1.1` or `Future research` item named in ADR-0019.
