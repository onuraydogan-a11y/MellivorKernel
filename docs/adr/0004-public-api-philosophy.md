# 0004. Public API philosophy

Status: Accepted
Date: 2026-07-18

## Context

Mellivor Kernel exists to be consumed by external applications, starting with
Mellivor One ([ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md)).
Before any subsystem is implemented, the repository needs a stated
philosophy for *how* a consuming application talks to the kernel: what shape
that interaction takes, what counts as a stable promise versus an
implementation detail, and how the kernel stays extensible without consumers
reaching into its internals. Without this, each subsystem would independently
improvise an API shape, producing an inconsistent surface and making the
compatibility guarantees in ADR-0005 impossible to state meaningfully.

This ADR is deliberately about philosophy, not a concrete interface
specification. Per-subsystem contracts are written up in `docs/specs/` as
each subsystem is designed, and must conform to the principles here.

## Decision

**Consumption model: library-first, in-process.** Mellivor Kernel is
consumed as a library/SDK embedded directly in the consuming application's
process (e.g. Mellivor One imports `mellivor_kernel`), not as a standalone
network service the product calls over the wire. This keeps latency low,
avoids operating a shared multi-tenant service the kernel team would have to
run, and lets each product own its own deployment topology. If a
service-mode deployment is ever needed (e.g. multiple independently deployed
products sharing one running kernel), it will be layered on top of the
library API as a separate adapter — it does not change the kernel's own API
philosophy, and is out of scope until a concrete need and a follow-up ADR
exist.

**The public surface is explicit, not incidental.** Each subsystem exposes a
documented, explicit set of contracts (interfaces/protocols) at its package
boundary (e.g. `mellivor_kernel.agents`, `mellivor_kernel.workflow`).
Anything not part of that documented contract is internal, may change
without notice, and is not something consuming applications should import or
depend on.

**Consuming applications interact with the kernel through four mechanisms
only:**

1. **Contracts** — each kernel responsibility (agent lifecycle, workflow
   engine, memory, tool execution, event bus, plugin loading, provider
   abstraction, configuration) is defined as an abstract contract first.
2. **Reference implementations** — the kernel may ship default
   implementations of its own contracts, but a consuming application may
   supply its own implementation of any contract (e.g. its own memory
   backend) as long as it satisfies that contract.
3. **Plugins** — behavior the kernel does not natively provide is added by a
   consuming application through the `plugins` subsystem, never by forking
   or monkey-patching kernel internals.
4. **Events** — cross-cutting, loosely-coupled communication (between the
   consuming application and the kernel, and between kernel subsystems)
   happens over the event bus rather than deep callbacks into consumer code.

**Errors are translated at the boundary.** The kernel raises a documented
hierarchy of kernel-specific exceptions at each public contract boundary. It
does not let provider-specific or implementation-specific exceptions (e.g. a
raw exception from an LLM provider's SDK) leak across the public API —
`providers/` is responsible for translating them into kernel exception types
before they propagate further.

**No implicit global state.** The public API has no global singleton kernel
instance. Consuming applications instantiate and explicitly configure the
kernel, which allows multiple independent kernel instances to coexist in one
process (e.g. for testing) and keeps configuration ownership with the
consumer, consistent with the `config` subsystem's role.

## Alternatives considered

- **Kernel-as-a-service by default** (consuming applications talk to it over
  HTTP/gRPC as a separately deployed service). Rejected as the primary model:
  disproportionate operational overhead for a foundation-stage kernel with
  one initial consumer. Left as a possible future adapter on top of the
  library API, not the default.
- **No formal contracts; consumers just call whatever is importable.**
  Rejected: unversionable and unreviewable, and makes the compatibility
  guarantees ADR-0005 needs to state impossible to define meaningfully.
- **A global singleton kernel instance.** Rejected: complicates testing and
  precludes a single process hosting more than one kernel configuration.

## Consequences

- Every subsystem spec written in `docs/specs/` must state its public
  contract explicitly — what is exported, what is covered by compatibility
  guarantees — before implementation of that subsystem begins.
- Consuming applications should never import from internal/private modules;
  the naming convention marking a module internal (e.g. a leading underscore
  or an `_internal` subpackage) will be fixed at implementation time but the
  principle is fixed now.
- Any future service-mode access is additive, built on top of the library
  API, and must not redefine the philosophy stated here.
