# Architecture Decision Records

This directory records the architecturally significant decisions made in
Mellivor Kernel: what was decided, why, what alternatives were considered,
and what tradeoffs were accepted.

## When to write an ADR

Write an ADR before (or alongside) any change that:

- Introduces or restructures a kernel subsystem.
- Defines or changes a contract/interface other subsystems or products will
  depend on.
- Adopts, replaces, or drops a significant dependency or provider adapter.
- Reverses or supersedes a previous architectural decision.

Small, local, easily reversible choices do not need an ADR.

## Process

1. Copy [`template.md`](template.md) to `NNNN-short-title.md`, where `NNNN`
   is the next sequential number (zero-padded to 4 digits).
2. Fill it in and set status to `Proposed`.
3. Once agreed, update status to `Accepted` (or `Rejected`).
4. If a later decision replaces this one, update this ADR's status to
   `Superseded by ADR-NNNN` and link the new one — never delete or rewrite
   history.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions with ADRs | Accepted |
| [0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) | Mellivor Kernel is an AI Enterprise Kernel, not a software development framework | Accepted |
| [0003](0003-repository-boundaries.md) | Repository boundaries | Accepted |
| [0004](0004-public-api-philosophy.md) | Public API philosophy | Accepted |
| [0005](0005-versioning-strategy.md) | Versioning strategy | Accepted |
| [0006](0006-execution-core-orchestration-layer.md) | Execution Core as the kernel's orchestration layer | Accepted |
| [0007](0007-authorization-engine-and-execution-decoupling.md) | Authorization Engine, decoupled from Execution Core via a structural contract | Accepted |
| [0008](0008-event-bus-and-lifecycle-events.md) | Event Bus, and lifecycle events published by Execution and Authorization | Accepted |
| [0009](0009-memory-subsystem-and-execution-recording.md) | Memory subsystem, and execution recording through it | Accepted |
| [0010](0010-workflow-engine-and-orchestration-boundary.md) | Workflow Engine, and the orchestration/execution boundary | Accepted |
