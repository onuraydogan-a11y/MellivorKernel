# 0001. Record architecture decisions with ADRs

Status: Accepted
Date: 2026-07-18

## Context

Mellivor Kernel is meant to be a long-lived, reusable foundation for multiple
products. Its subsystem boundaries, contracts, and provider integrations will
be revisited many times, by people who were not present for the original
reasoning. Without a record, decisions get silently re-litigated or silently
violated as the codebase grows.

## Decision

Architecturally significant decisions in this repository are recorded as
Architecture Decision Records (ADRs) in `docs/adr/`, following the process in
[`docs/adr/README.md`](README.md).

## Alternatives considered

- **No formal record, rely on commit messages / PR descriptions.** Rejected:
  these are hard to discover later and are not indexed as decisions.
- **A single evolving design doc instead of discrete records.** Rejected:
  loses the history of *why* a decision was made and what was rejected;
  `docs/architecture.md` serves as the current-state summary, while ADRs
  preserve the decision trail behind it.

## Consequences

- Every subsystem-shaping change should be traceable to an ADR.
- `docs/architecture.md` is expected to reflect the cumulative effect of
  accepted ADRs, not to duplicate their reasoning.
- Adds a small amount of process overhead before structural changes; accepted
  as worthwhile given the kernel's intended lifespan and number of consumers.
