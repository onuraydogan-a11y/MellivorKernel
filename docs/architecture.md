# Mellivor Kernel — High-Level Architecture

Status: Foundation. This document describes the intended shape of the kernel.
Subsystems described here are design targets, not yet implementations.

This document reflects the scope decision recorded in
[ADR-0002](adr/0002-ai-enterprise-kernel-scope-and-subsystems.md). Read that
ADR for the full rationale; this document tracks its current-state summary.

## What the kernel is

Mellivor Kernel is an **AI Enterprise Kernel**, not a software development
framework. Its purpose is to power enterprise AI applications — starting with
Mellivor One — by providing the AI substrate those applications are built on.

## What the kernel is not

The kernel is strictly **business-agnostic**. It must never contain CRM,
Legal, HR, Finance, Security, or any other business/domain logic. That logic
always lives in external, consuming applications. Nothing in this repository
should assume, encode, or special-case any business vertical.

## Guiding principles

See [`docs/architecture/principles.md`](architecture/principles.md) for the
kernel's guiding principles (moved there in Sprint 5's docs
reorganization).

## Kernel responsibilities

Per ADR-0002, the kernel's responsibilities are limited to exactly:

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

## Subsystems (`src/mellivor_kernel/`)

```
                 ┌─────────────────────────────┐
                 │             core             │
                 │   lifecycle, contracts,      │
                 │   dependency boundaries      │
                 └───────────────┬───────────────┘
                                  │
   ┌─────────┬─────────┬─────────┼─────────┬─────────┬─────────┐
   │          │          │         │          │          │          │
┌──▼───┐ ┌───▼────┐ ┌───▼───┐ ┌──▼───┐ ┌───▼────┐ ┌───▼───┐ ┌───▼───┐
│agents│ │workflow│ │memory │ │tools │ │ events │ │plugins│ │ config│
└──┬───┘ └───┬────┘ └───┬───┘ └──┬───┘ └───┬────┘ └───┬───┘ └───┬───┘
   │          │          │         │          │          │          │
   └──────────┴──────────┴────┬────┴──────────┴──────────┴──────────┘
                                │
                          ┌─────▼──────┐
                          │  providers  │
                          │ (multi-LLM, │
                          │  external   │
                          │  systems)   │
                          └─────────────┘
```

- **`core`** — Kernel bootstrapping and lifecycle, shared contracts/types,
  dependency-injection boundaries. The only subsystem every other subsystem
  may depend on.

- **`agents`** — Agent lifecycle: creation, state, execution, and teardown of
  individual AI agents, independent of any single model provider.

- **`workflow`** — The workflow engine: composing agents and tools into
  multi-step processes, including routing and scheduling of that work.

- **`memory`** — Memory abstraction: contracts for short-term
  (session/conversation) and long-term (persistent, retrievable) memory,
  without committing to a specific store.

- **`tools`** — Tool execution: registration, invocation, input/output
  schemas, and execution boundaries (including sandboxing concerns) for
  anything the kernel can call out to.

- **`events`** — The event bus: publish/subscribe primitives used for
  communication between kernel subsystems and, indirectly, between agents
  and workflows.

- **`plugins`** — Plugin loading: discovery, registration, and lifecycle of
  pluggable extensions to the kernel.

- **`config`** — Configuration: contracts for configuration and environment
  loading (including feature flags), kept separate so products can supply
  their own configuration sources without the kernel assuming any one
  mechanism.

- **`providers`** — Multi-LLM provider abstraction: pluggable integrations to
  model providers and related external systems. This is the only place
  provider-specific code is allowed to live; providers implement contracts
  defined by the other subsystems and are swappable and independently
  versioned.

### AI orchestration: placed in `execution` (Sprint 6)

Per [ADR-0006](adr/0006-execution-core-orchestration-layer.md), the
**AI orchestration** responsibility named above is implemented by
`execution`, a top-level package alongside `bootstrap` rather than one of
the seven subsystems in the diagram: it orchestrates *running* work across
`tools` and `providers` (dispatch, execution lifecycle), the same way
`bootstrap` composes them into a running kernel. `execution` depends on
`tools` and `providers`; neither depends back on it.

### Partially placed: Observability. Not yet placed: Security primitives

Structured logging — the first slice of the Observability responsibility —
is implemented in `core/logging.py` (Sprint 2), using the fallback ADR-0002
itself anticipated ("hosted inside `core/`") rather than a new top-level
package. Tracing, metrics, and audit trail remain unaddressed.

Security primitives do not yet have any implementation or placement. This
remains a deliberate open point, not an omission — see ADR-0002. A future
ADR will decide whether Security (and the rest of Observability) become
their own top-level package(s) or continue to be hosted inside `core/`.

## The composition layer (`src/mellivor_kernel/bootstrap/`)

`core` owns the kernel runtime's own bootstrap/lifecycle sequence
(`core.runtime.Kernel.start()`/`.shutdown()`), consistent with its
description above. Composing multiple subsystems together into one running
kernel is a distinct, higher-level concern that cannot live inside `core`
(or any single subsystem) without that subsystem depending on its siblings
— which would break the acyclic dependency graph the subsystems otherwise
maintain (`core` depends on nothing else; `config`/`providers`/`tools` each
depend only on `core`).

`bootstrap` is a top-level package, a peer to the subsystems above rather
than one of them, that assembles `config` + `core` + `providers` + `tools`
into a running kernel (`KernelBootstrap`, `BootstrapBuilder`) and exposes a
read-only view of the result (`RuntimeContext`) to consumers. It is not a
new kernel *responsibility* under the list above — it composes
responsibilities that already exist — so its addition did not require
amending that list.

## The execution layer (`src/mellivor_kernel/execution/`)

`execution` is a top-level package, a peer to `bootstrap` rather than one of
the subsystems above, that orchestrates execution across them: an
`ExecutionEngine` validates and runs an `ExecutionRequest` by dispatching it
(`Dispatcher`) to the Tool Runtime or the Provider Runtime and returning a
common `ExecutionResult`. See
[`docs/specs/execution.md`](specs/execution.md) and
[ADR-0006](adr/0006-execution-core-orchestration-layer.md) for the full
contract and the rationale for placing it here rather than inside `tools`
or `providers`.

Execution Core is orchestration only: authorization, retries, workflow
composition, and the event bus remain future work, exactly as they were
before this sprint — `execution` does not anticipate their shape.

## Consumption model

Products — Mellivor One, and future enterprise products — depend on the
kernel as a library: they compose kernel subsystems and supply providers for
the model(s) they need. Business logic, UI, and domain modules live entirely
in the consuming product, never in this repository. As of Sprint 5, this
composition has a concrete mechanism — `mellivor_kernel.bootstrap` — rather
than being something each consuming product had to hand-roll itself.

## How this document evolves

Changes to subsystem boundaries, the kernel's responsibility list, or the
principles in [`docs/architecture/principles.md`](architecture/principles.md)
should be proposed and recorded as an ADR in [`docs/adr/`](adr/README.md)
before this document is updated to match.
