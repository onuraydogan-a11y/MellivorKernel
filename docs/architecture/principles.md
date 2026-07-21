# Architectural Principles

Moved from `docs/architecture.md`'s "Guiding principles" section (Sprint 5
docs reorganization) into its own file. These principles govern how
Mellivor Kernel evolves; see
[ADR-0002](../adr/0002-ai-enterprise-kernel-scope-and-subsystems.md) for
the decision they're derived from, and
[`docs/architecture.md`](../architecture.md) for the current-state summary
of the architecture they govern.

1. **AI Enterprise Kernel, not a framework.** The kernel exists to power
   enterprise AI applications, not to be a general-purpose application
   framework. Capabilities are added because an enterprise AI application
   needs them from the kernel specifically, not because they would be
   generically useful.
2. **Business-agnostic, always.** No CRM, Legal, HR, Finance, Security, or
   other domain logic, ever — regardless of how small or temporary it is
   claimed to be. See ADR-0002.
3. **Provider-agnostic core.** Nothing outside `providers/` may depend
   directly on a specific model provider, vector database, or external
   SaaS. `providers/` is the only place provider-specific code is allowed to
   live.
4. **Contracts before implementations.** Each subsystem is defined first by
   its interface/contract, documented via an ADR and/or spec, before any
   concrete implementation is added.
5. **Composability over configuration sprawl.** Products assemble kernel
   subsystems as building blocks rather than fighting a monolithic
   framework.
6. **Observability is not optional.** Every subsystem is expected to be
   inspectable (logs, traces, metrics, audit events) once the observability
   subsystem is designed, rather than inventing its own instrumentation.
7. **Minimal surface area.** The kernel grows by deliberate, documented
   decisions (ADRs), not by accretion. The current fixed list of kernel
   responsibilities is enumerated in
   [`docs/architecture.md`](../architecture.md#kernel-responsibilities);
   nothing outside it belongs in the kernel without a new ADR expanding it.

## How these principles evolve

Changes to these principles should be proposed and recorded as an ADR in
[`docs/adr/`](../adr/README.md) before this document is updated to match.
