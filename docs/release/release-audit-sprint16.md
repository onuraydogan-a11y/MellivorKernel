# Release Audit — Post Security & Observability Foundations (Sprints 15–16)

Audit date: 2026-07-23
Audited commit: `7b115f7` (`docs(kernel): document observability foundation`)
Branch: `main`
Remote status at audit start: `main` matched `origin/main`

This audit succeeds and extends
[`docs/release/release-audit.md`](release-audit.md) (Sprint 14, Integration
Gate #2, audited at `548a95a`). That document is preserved as-is and remains
the historical record of the `v0.13.0` release-candidate state before the
Security and Observability Foundation sprints. This document covers what
changed since: Sprint 15 (`security`, ADR-0012) and Sprint 16
(`observability`, ADR-0013), both shipped as documented, foundation-only
packages per the Sprint 14 audit's own risk ordering.

## Executive Summary

The repository remains internally consistent at the current commit. Adding
`security` and `observability` introduced two new top-level packages, nine
new tests, and no change to any previously implemented subsystem's public
contract, dependency direction, or behavior. No circular imports, no
package-boundary violation, no missing public export, and no failing example
were found. As part of this audit, the cross-cutting documentation set
(`docs/architecture/roadmap.md`, `docs/architecture.md`, `docs/adr/README.md`,
`docs/specs/README.md`, `README.md`) was found to be out of sync with the
implementation — both new packages existed in source, tests, ADRs, and specs
without being reflected in the roadmap, architecture overview, ADR index,
specs index, or README — and has been corrected as part of this
documentation-synchronization sprint. No production code or test was
modified to make these corrections.

## Architecture Review

The implemented package structure now includes two additional top-level
packages beyond the Sprint 14 audit's scope:

- `security` — foundation-only security contracts and primitives (`Secret`,
  `SecretProvider`, `SecretProviderRegistry`, `SecurityPolicy`,
  `SecurityDecision`, `SecureConfiguration`, `AuditRecord`, `AuditSink`).
  Depends only on `core` (for `KernelError`). Not imported by any other
  kernel package.
- `observability` — foundation-only observability contracts and no-op
  defaults (`ObservationContext`, `MetricsRecorder`, `TraceRecorder`/
  `TraceSpan`, `StructuredEventSink`/`StructuredObservationEvent`,
  `Observability`). Depends on no other kernel package, including `core`.
  Not imported by any other kernel package.

Every other subsystem's boundary matches the Sprint 14 audit unchanged:
`core` owns shared lifecycle, contracts, DI, and logging; `config`,
`providers`, and `tools` depend on `core`; `events` and `memory` depend on
`core`; `execution` composes tool and provider execution; `authorization` is
consulted through a structural contract; `workflow` composes execution,
memory, and events; `agents` composes workflow, memory, and events;
`bootstrap` composes the runtime-facing subsystems; `plugins` remains an
empty skeleton. All 86 source modules (up from 74 at the Sprint 14 audit)
imported successfully. No architecture change is recommended.

## Dependency Review

Updated package-level import graph:

```text
agents        -> core, events, memory, workflow
authorization -> core, events, execution, tools
bootstrap     -> config, core, execution, providers, tools
config        -> core
events        -> core
execution     -> core, events, memory, providers, tools
memory        -> core
observability -> (none)
plugins       -> none
providers     -> core
security      -> core
tools         -> core
workflow      -> core, events, execution, memory
core          -> none
```

`security` and `observability` are the only two packages added since Sprint
14. Neither is imported by any existing subsystem, and neither imports
anything outside `core` (and, for `observability`, not even that). The graph
remains acyclic; no strongly connected component contains more than one
package. Provider-specific code remains confined to `providers`.

## Public API Review

Sixteen export surfaces were checked (fourteen at the Sprint 14 audit, plus
`security` and `observability`). Every declared `__all__` symbol resolves on
its owning package after import — verified by importing all sixteen surfaces
and asserting every exported name exists. The two new surfaces are limited
to contracts, dataclasses, protocols, exceptions, and no-op reference
implementations, consistent with both ADRs' "foundation-only" scope
statement. No unplanned public API expansion or accidental export was found.

## Bootstrap Review

Unchanged from Sprint 14. `BootstrapBuilder`/`KernelBootstrap` compose
`config` + `core` + `providers` + `tools`; `ExecutionEngine`,
`AuthorizationEngine`, `WorkflowEngine`, `AgentEngine`, and now `security`
and `observability` are not wired in automatically. This remains a
documented, deliberate limitation, not a defect — see Release Risks below.

## Documentation Review

This audit found, and this synchronization sprint corrected, the following
staleness (all documentation-only changes, no code or test touched):

- `docs/architecture/roadmap.md` — narrative and sprint table stopped at
  Sprint 13A; Sprint 14 (Integration Gate #2) was undocumented in the
  roadmap itself, and Sprints 15–16 (Security/Observability Foundations)
  were listed only in the "not scheduled" backlog despite being shipped.
  **Corrected**: narrative and table now run through Sprint 16; the backlog
  paragraph now reflects only what remains genuinely unscheduled (plugin
  loading, richer agent behavior, additional providers, dynamic/parallel
  workflow execution, memory persistence/RAG, and the remainder of Security
  and Observability beyond their Sprint 15/16 foundations).
- `docs/architecture.md` — status line and both "partially placed" sections
  did not mention `security` or `observability` as existing packages.
  **Corrected**: status line, and dedicated subsections for both packages
  (mirroring the existing `authorization`/structured-logging sections),
  now describe what each foundation does and does not cover.
- `docs/adr/README.md` — the ADR index table stopped at ADR-0011, omitting
  ADR-0012 and ADR-0013 even though both files exist and are `Accepted`.
  **Corrected**: both rows added.
- `docs/specs/README.md` — the specs index stopped at `agents.md`, omitting
  `security.md` and `observability.md`. **Corrected**: both added.
- `README.md` — the Status section, "Implemented so far" narrative, and
  repository-layout code block did not mention `security` or
  `observability`. **Corrected**: all three updated; the roadmap link
  (`docs/architecture/roadmap.md`) was verified unchanged and correct.

A pre-existing sprint-numbering ambiguity was identified but **not**
corrected as part of this sprint (see Remaining Drift, in the accompanying
consistency report): `docs/specs/security.md` and
`docs/specs/observability.md` each carry a `Status: Foundation (Sprint N)`
line reading Sprint 14 and Sprint 15 respectively, which collides with
Sprint 14 already being claimed by the preserved Sprint 14 Integration Gate
#2 audit. This roadmap now treats Security Foundation as Sprint 15 and
Observability Foundation as Sprint 16, consistent with actual commit order
(the release audit landed before the security-foundation commit, which
landed before the observability-foundation commit). The two spec files'
internal labels were left untouched, since editing them was outside this
sprint's assigned scope (`docs/architecture/roadmap.md`,
`docs/architecture.md`, ADR consistency, release documentation, and
`README.md`).

## Dead Code Review

Ruff reports no unused imports or other configured static dead-code
findings across all 189 formatted files. `security` and `observability`
introduce no dead exports: every declared `__all__` symbol is exercised by
at least one test in `tests/security/test_foundation.py` or
`tests/observability/test_foundation.py`. The empty `plugins` package
remains a documented, intentional placeholder, not dead code.

## Release Risks

Updated from the Sprint 14 audit — two items resolved to foundation-level,
the remainder unchanged:

- Plugin discovery, registration, and lifecycle are still not implemented.
- The agent runtime is still limited to one workflow with no planning,
  reasoning, reflection, dynamic workflow selection, or multi-agent
  composition.
- Workflow execution is still sequential only.
- Memory is still text-only and in-memory.
- Only the Claude provider has a concrete implementation.
- ~~Security primitives beyond authorization... remain unaddressed~~ →
  **Partially resolved.** A dedicated `security` foundation now exists
  (contracts, secrets, policy, audit). Concrete secret backends,
  authentication, OAuth, SSO, RBAC, and encryption remain unaddressed, and
  the foundation is not yet consumed by any other subsystem.
- ~~Observability beyond structured logging... remains unaddressed~~ →
  **Partially resolved.** A dedicated `observability` foundation now exists
  (contracts, correlation IDs, no-op metrics/tracing/event sinks). Concrete
  metrics/tracing backends, vendor integration, telemetry export, and a
  trace/audit consumer built on `events` remain unaddressed, and the
  foundation is not yet consumed by any other subsystem.
- Bootstrap still does not automatically compose the newer engines, and now
  also does not compose `security` or `observability`.
- **New risk**: neither `security` nor `observability` has been dogfooded
  internally (CLAUDE.md §13) — no kernel subsystem consumes either
  foundation yet, so their contract shapes are unproven against a real call
  path.

## Production Readiness

For the current `v0.13.0` release-candidate scope, unchanged from Sprint 14
except as noted:

- Package boundaries: pass.
- Dependency direction: pass (two new leaf packages added, graph still
  acyclic).
- Circular-import check: pass.
- Public exports: pass (sixteen surfaces, up from fourteen).
- Bootstrap integration: pass (unchanged; still manual for the newer
  engines and the two new foundations).
- Examples: pass, 4 of 4 executed successfully (no new example added for
  `security`/`observability` — see dogfooding risk above).
- Documentation links and cross-references: pass, after the corrections
  made in this sprint.
- Test, lint, formatting, and type-check gates: pass — 456 tests (up from
  447), `ruff check` clean, `ruff format --check` clean (189 files), `mypy
  --strict` clean (184 source files).

The kernel is not production-complete as a general enterprise AI runtime for
`1.0.0`; the release risks above remain open. It is production-ready only
for consumers that accept the explicitly documented `v0.13.0` scope.

## Final Recommendation

**Approve the post-Sprint-16 repository state as consistent and
documentation-synchronized.** No code defect was found or introduced by
this audit or its accompanying documentation sprint; only documentation
files were changed, and no test or production code was modified. **Do not
declare `1.0.0` yet.** The next highest-value engineering work is dogfooding
`security` and `observability` into an existing subsystem (see the
accompanying consistency report's recommended next sprint), not further
expansion of either foundation or a move to plugin loading.

## Verification Record

The following commands completed successfully at the audited commit:

```text
pytest                 456 passed
ruff check .           All checks passed!
ruff format --check .  189 files already formatted
mypy                   Success: no issues found in 184 source files
examples/*.py          4 of 4 executed successfully
```
