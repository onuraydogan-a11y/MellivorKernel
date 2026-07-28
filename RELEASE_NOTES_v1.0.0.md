# Mellivor Kernel v1.0.0

Commit: this release commit (`release(v1.0): declare Mellivor Kernel 1.0.0`) · Branch: `main`
Tag: `v1.0.0` — applied manually after final human review, per the release
governance sequence; not yet cut as of this file's commit.

Governance decision: [ADR-0020](docs/adr/0020-release-decision-v1.0.md).
Scope lock: [ADR-0019](docs/adr/0019-release-readiness-and-scope-lock.md).
Full readiness record: [`docs/release/v1.0-release-checklist.md`](docs/release/v1.0-release-checklist.md).

## Summary

Mellivor Kernel's first stable release. Twenty-six sprints of implementation,
from the `core`/`config`/`providers`/`tools`/`bootstrap` foundation (Sprints
1–5, recorded in [`RELEASE_NOTES_v0.5.0.md`](RELEASE_NOTES_v0.5.0.md))
through the AI Engine composition layer and a second concrete provider
(Sprints 22–23), culminate in every [ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md)
responsibility carrying a stable, documented public contract. Sprint 24
([ADR-0019](docs/adr/0019-release-readiness-and-scope-lock.md)) classified
that scope precisely; Sprint 25 resolved its one remaining closing action
and approved the public API/compatibility policy; Sprint 26 recorded a full
verification run and confirmed documentation/examples parity. ADR-0020
records the release decision itself.

`1.0.0` is a scope and compatibility milestone, not a feature-completeness
claim: several responsibilities intentionally ship a stable baseline slice
with richer capability explicitly deferred — see "Deferred scope" below.
Nothing was removed or broken to reach this release.

## Architecture

Eighteen packages under `src/mellivor_kernel/`, an acyclic dependency graph
rooted at `core` (the only package every other package may depend on):

```
core → { agents, workflow, memory, tools, events, plugins, config }
config, providers, tools → core
execution → core, events, memory, providers, tools
authorization → core, events, execution, tools
workflow → core, events, execution, memory
agents → core, events, memory, workflow
security, observability → dependency-injected, structurally separate
plugins → core; plugin_sdk → plugins; plugins_builtin → plugin_sdk, plugins, providers, tools, core
plugin_discovery → plugins, core
bootstrap → config, core, providers, tools
ai_engine → core, bootstrap, execution, authorization, workflow, agents,
            memory, events, security, observability, plugins, plugin_discovery
```

See [`docs/architecture.md`](docs/architecture.md) for the full narrative
and [`docs/architecture/roadmap.md`](docs/architecture/roadmap.md) for the
sprint-by-sprint history behind each package.

## Public API

157 exported symbols (`__all__`) across 20 importable modules, every one
verified importable at release time (`pytest`, Sprint 26 re-verification):

| Module | Exports |
|---|---|
| `mellivor_kernel` | 1 |
| `mellivor_kernel.core` | 13 |
| `mellivor_kernel.config` | 4 |
| `mellivor_kernel.providers` | 9 |
| `mellivor_kernel.tools` | 16 |
| `mellivor_kernel.tools.builtin` | 3 |
| `mellivor_kernel.bootstrap` | 4 |
| `mellivor_kernel.execution` | 14 |
| `mellivor_kernel.authorization` | 8 |
| `mellivor_kernel.events` | 6 |
| `mellivor_kernel.memory` | 7 |
| `mellivor_kernel.workflow` | 10 |
| `mellivor_kernel.agents` | 9 |
| `mellivor_kernel.security` | 10 |
| `mellivor_kernel.observability` | 10 |
| `mellivor_kernel.plugins` | 14 |
| `mellivor_kernel.plugin_sdk` | 8 |
| `mellivor_kernel.plugins_builtin` | 2 |
| `mellivor_kernel.plugin_discovery` | 6 |
| `mellivor_kernel.ai_engine` | 3 |

Public contract per package is documented in [`docs/specs/`](docs/specs/README.md);
anything not listed there or in a package's `__all__` is internal and carries
no compatibility guarantee, per [ADR-0004](docs/adr/0004-public-api-philosophy.md).

## Included scope

Per [ADR-0019](docs/adr/0019-release-readiness-and-scope-lock.md), every
`Included in v1.0` item is satisfied with no open closing action:

- AI orchestration, tool execution, and configuration — full contracts, no
  known gap.
- Agent lifecycle — baseline: one agent invokes exactly one workflow.
- Workflow engine — sequential composition of `ExecutionEngine` calls.
- Memory abstraction — text/in-memory (`InMemoryStore`).
- Event bus — in-process (`InMemoryEventBus`).
- Plugin loading — runtime, SDK, filesystem discovery, one built-in plugin
  (`SystemInfoPlugin`).
- Multi-LLM provider abstraction — `BaseProvider` contract plus two concrete
  providers, `ClaudeProvider` and `OpenAIProvider`.
- Observability and security primitives — structured logging, contracts
  foundations, and audit/event wiring, as a "bring your own backend" story.

## Deferred scope

Not part of the `1.0.0` compatibility promise. Full detail in
`docs/release/v1.0-release-checklist.md`'s "Current limitations" section.

**Deferred to v1.1** (scoped, schedulable directly, no further design gate):
dynamic/parallel/scheduled workflow execution; a persistent `MemoryStore`;
additional concrete providers (Gemini, local models); a concrete
`SecretProvider` backend.

**Future research** (open-ended, no committed design or timeline): agent
planning/reasoning/reflection/multi-agent composition; embeddings/vector
search/RAG; distributed event delivery; plugin marketplace, remote plugins,
sandboxing, hot reload, signature verification, package installation; a
concrete metrics/tracing vendor integration; authentication, OAuth, SSO,
RBAC, encryption-at-rest.

## Verification summary

Recorded in `docs/release/v1.0-release-checklist.md`'s Verification Record.
Sprint 26 run (commit `ffbb250`): 717 tests passed, `ruff check .` clean,
`ruff format --check .` clean (311 files), `mypy` clean (246 source files,
strict mode). Re-verified fresh as part of this release's Phase 3, against
the actual release commit — see that section for the exact, current result.

## Compatibility statement

`1.0.0` is the first version governed by [ADR-0005](docs/adr/0005-versioning-strategy.md)'s
post-1.0 SemVer discipline: a breaking change to any documented public
contract requires a MAJOR version bump; backward-compatible additions
require MINOR; backward-compatible fixes require PATCH only. A public
contract element slated for removal must first be deprecated in a MINOR
release, with a documented migration path, and may not be removed before
the next MAJOR release. Compatibility guarantees apply only to the
documented public API surface above — internal modules and undocumented
behavior carry no promise and may change in any release, including PATCH.
