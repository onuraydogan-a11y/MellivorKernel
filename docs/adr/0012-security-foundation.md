# 0012. Introduce a dedicated `security` subsystem for reusable kernel security primitives

Status: Accepted
Date: 2026-07-23

## Context

ADR-0002 names **Security primitives** as a fixed kernel responsibility but
leaves its package placement open. The current codebase already contains a
partial slice of that responsibility in `authorization`, but the rest of the
kernel's security foundation remains unplaced.

A future `1.0.0` release cannot responsibly claim enterprise readiness while
security primitives remain only partially modeled. The repository also has a
clear boundary rule: business and product-specific security logic must stay
outside this kernel. That means the kernel needs a small, reusable security
foundation package that can be dependency-injected into future product-facing
features without making `execution`, `workflow`, `agents`, or `providers`
responsible for policy implementation.

## Decision

Introduce a new top-level package, `src/mellivor_kernel/security/`, whose
responsibility is limited to reusable kernel security infrastructure:

- security contracts
- secret abstraction
- secret provider interface
- secure configuration abstraction
- security policy abstraction
- audit contracts
- common security exceptions

This package is deliberately foundation-only. It does not implement
authentication, OAuth, SSO, RBAC, networking, UI interactions, or any
Mellivor One functionality. It also does not impose any product-specific
security model on consumers.

The subsystem is dependency-injected and remains structurally separate from
`execution`, `workflow`, `agents`, and `providers`. Those subsystems keep
their existing dependency boundaries and are not expected to import the
security package directly unless they choose to consume a protocol seam.

## Consequences

- The kernel now has a dedicated, business-agnostic security foundation
  package where reusable contract and abstraction work can live.
- The `authorization` subsystem remains the current policy-enforcement slice
  for execution permission checks; it is not replaced by this new package.
- Consumers can compose security components explicitly through dependency
  injection rather than by introducing new kernel-wide coupling.
- The architecture remains compatible with ADR-0002 and ADR-0003 because the
  new subsystem is kernel-owned infrastructure, not a product business
  capability.
