# 0003. Repository boundaries

Status: Accepted
Date: 2026-07-18

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) defined the
kernel's scope in terms of *capabilities*: the fixed list of responsibilities
the kernel is allowed to implement, and the package layout those map to.
That answers "does this capability belong in the kernel." It does not answer
the many other boundary questions a growing repository accumulates: whether
a given test fixture, example, dependency, CI job, or piece of documentation
belongs here — especially when it doesn't look like "business logic" on its
face but still couples the kernel to something it shouldn't know about.

This ADR exists so contributors and reviewers have a concrete, citable answer
to "does X belong in this repository" without re-deriving it from first
principles every time.

## Decision

### Belongs in this repository

- Kernel subsystem code implementing the responsibilities enumerated in
  ADR-0002, under `src/mellivor_kernel/`.
- Kernel-level tests exercising kernel contracts, using synthetic,
  business-agnostic fixtures (e.g. a toy domain) rather than data resembling
  any real Mellivor product or customer.
- Kernel-level documentation: architecture docs, ADRs, and specs.
- Minimal, illustrative examples demonstrating kernel usage in the abstract
  (e.g. a toy agent or workflow) — never a scaled-down resemblance of a real
  Mellivor product or business domain.
- Developer/maintenance tooling for the kernel itself (lint, test, release
  scripts) and kernel-level CI configuration.
- Integrations with **infrastructure** providers that the kernel's contracts
  are defined in terms of: LLM/model providers, vector stores, caches,
  message brokers, and similar generic technical infrastructure, under
  `providers/`.

### Must never belong in this repository

- Any business/domain logic — CRM, Legal, HR, Finance, Security-as-a-business-
  module, or any other business vertical — restated from ADR-0002. This
  applies regardless of how small, isolated, or "temporary" it is claimed to
  be.
- UI code of any kind: web, product CLI, dashboards. (Developer tooling for
  maintaining the kernel itself, e.g. a release script, is not UI in this
  sense.)
- Integrations with **business-application** SaaS products — CRM, HRIS,
  ERP/Finance systems, ticketing/support systems, and the like. These encode
  assumptions about a specific business vertical even when framed as "just an
  adapter," and belong in the consuming application's own integration layer,
  which may call into the kernel's `tools` contract if it needs to invoke the
  kernel.
- Product-specific configuration, secrets, credentials, or any customer/
  tenant data — including inside tests, fixtures, or examples.
- Deployment or infrastructure-as-code for any specific product or
  environment (e.g. Mellivor One's Kubernetes manifests or Terraform).
- Anything that hard-codes an assumption about a specific product, tenant, or
  business vertical.
- Forked or vendored copies of a consuming application's code, kept here "for
  convenience."

### Deciding the infrastructure vs. business-application line

The test for whether an external integration belongs under `providers/` is
whether the kernel's own contracts (as defined by its responsibility list)
are naturally defined in terms of it — a model provider or a vector store is
infrastructure the `providers`, `memory`, and `tools` contracts already
presuppose. A CRM or HRIS is not presupposed by any kernel contract; it is a
business application the kernel has no reason to know exists.

## Alternatives considered

- **Rely solely on ADR-0002's responsibility list as the boundary.**
  Rejected: that list defines capabilities, not the many other artifact
  types (tests, examples, dependencies, CI, docs) that also raise boundary
  questions, and reviewers need concrete categories to point to during
  review rather than re-deriving intent each time.
- **Enforce boundaries only through informal code-review judgment.**
  Rejected for the same reason as ADR-0001: undocumented judgment calls get
  relitigated and drift as reviewers change.

## Consequences

- Code review can cite this ADR directly when rejecting an out-of-scope
  contribution.
- Examples and tests must use synthetic, business-agnostic data — never
  anything resembling a real Mellivor product or customer.
- Proposed dependencies on business-application SaaS SDKs should be rejected
  or redirected to the consuming application.
- This ADR does not enumerate every possible artifact type in advance.
  Genuinely ambiguous cases should be resolved by amending this ADR or
  writing a new one, not by improvisation.
