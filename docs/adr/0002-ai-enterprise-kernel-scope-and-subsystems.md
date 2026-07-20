# 0002. Mellivor Kernel is an AI Enterprise Kernel, not a software development framework

Status: Accepted
Date: 2026-07-18

## Context

The initial architecture (recorded directly in `docs/architecture.md`, prior
to this ADR) described Mellivor Kernel using generic, framework-flavored
subsystem names (`reasoning`, `orchestration`, `adapters`, `observability`)
under a generic `src/kernel/` package. That vocabulary is broad enough to
describe almost any AI application framework, which creates two risks as the
kernel grows:

1. **Scope creep toward a general-purpose framework.** Without a sharper
   definition, contributors could reasonably add capabilities that make the
   kernel more broadly "useful" but are not actually about powering
   enterprise AI applications — pulling it toward being a framework rather
   than a kernel.
2. **Business logic leaking into the kernel.** Mellivor One and future
   products will need CRM-, Legal-, HR-, Finance-, and Security-flavored
   capabilities. Without an explicit, written boundary, it is tempting to
   implement fragments of that domain logic "just this once" inside the
   kernel, where it will be nearly impossible to remove later.

This decision fixes both by naming what the kernel is, what it is
categorically not, and by renaming/reorganizing its packages to match its
actual responsibilities rather than generic framework terminology.

## Decision

**Mellivor Kernel is an AI Enterprise Kernel, not a software development
framework.** Its purpose is to power enterprise AI applications — starting
with Mellivor One — by providing the AI substrate those applications are
built on.

**The kernel is strictly business-agnostic.** It must never contain CRM,
Legal, HR, Finance, Security, or any other business/domain logic. That logic
always lives in external, consuming applications. This repository will
reject any contribution that implements a business capability rather than a
kernel capability, regardless of how small or "temporary" it is claimed to
be.

**The kernel's responsibilities are limited to exactly:**

- AI orchestration
- Agent lifecycle
- Workflow engine
- Memory abstraction
- Tool execution
- Event bus
- Plugin loading
- Multi-LLM provider abstraction
- Configuration
- Observability
- Security primitives

Nothing outside this list belongs in the kernel without a new ADR expanding
it.

**Package layout** is reorganized under `src/mellivor_kernel/` to name
packages after these responsibilities directly, replacing the previous
generic `src/kernel/` layout:

| New package (`src/mellivor_kernel/`) | Responsibility                         | Supersedes / relates to prior layout |
|---------------------------------------|-----------------------------------------|----------------------------------------|
| `core`                                 | Shared lifecycle, contracts, DI boundary | `core` (unchanged in intent) |
| `agents`                               | Agent lifecycle                          | `reasoning` |
| `workflow`                             | Workflow engine                          | `orchestration` |
| `memory`                               | Memory abstraction                       | `memory` (unchanged) |
| `providers`                            | Multi-LLM provider abstraction           | `adapters` (narrowed: model providers specifically; non-LLM integrations are addressed separately if/when needed) |
| `tools`                                | Tool execution                           | `tools` (unchanged) |
| `events`                               | Event bus                                | new, split out as its own concern |
| `plugins`                              | Plugin loading                           | new, split out as its own concern |
| `config`                               | Configuration                            | `config` (unchanged) |

**Open point — not yet decided:** Observability and Security primitives
remain named kernel responsibilities but do not yet have a dedicated
top-level package under `src/mellivor_kernel/`. They are deferred rather than
silently dropped; a future ADR will decide whether each gets its own
top-level package (e.g. `observability/`, `security/`) or is hosted inside
`core/`, once their design is worked out.

## Alternatives considered

- **Keep the kernel general-purpose enough to double as a reusable
  application framework** (i.e., useful for non-AI, non-enterprise use
  cases too). Rejected: dilutes focus, and a framework-shaped kernel is
  exactly the shape that invites business logic to creep in over time.
- **Keep the original generic subsystem names** (`reasoning`, `orchestration`,
  `adapters`, `observability`) under `src/kernel/`. Rejected in favor of
  vocabulary that names capabilities the way an enterprise kernel consumer
  (e.g. Mellivor One) actually thinks about them: agents, workflows,
  providers, events, plugins.
- **Fold Observability and Security primitives into existing packages now**
  (e.g. inside `core/`) rather than leaving them as an open point. Rejected
  for this ADR: neither subsystem's design has been discussed yet, and
  guessing their placement now risks a shape that has to be undone later.
  Left explicit as future work instead.

## Consequences

- Any future proposal to add CRM, Legal, HR, Finance, Security-as-a-business-
  module, or other domain logic to this repository should be pointed at this
  ADR and redirected to a consuming application.
- `docs/architecture.md` and `README.md` are updated to reflect this scope
  statement and the new package layout.
- `src/kernel/` (generic layout) is retired in favor of `src/mellivor_kernel/`
  as described above. No functionality existed in either layout at the time
  of this change, so no migration was required.
- Observability and Security primitives are tracked as unresolved design
  work; they should not be assumed to live in any particular package until a
  follow-up ADR places them.
