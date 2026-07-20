# 0005. Versioning strategy

Status: Accepted
Date: 2026-07-18

## Context

Mellivor Kernel will be depended on by multiple products over time — Mellivor
One first, others later — each potentially upgrading on its own schedule. The
kernel needs a stated policy for what its version number means, what is
covered by a compatibility promise, and how deprecated functionality is
retired, fixed now so it constrains API design ([ADR-0004](0004-public-api-philosophy.md))
going forward rather than being retrofitted after consumers already depend on
undocumented behavior.

## Decision

**Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`) governs the kernel's
published package version:

- **MAJOR** — a breaking change to any public contract as defined in
  ADR-0004: removing or renaming a public interface, an incompatible
  signature change, or a change to documented behavior a consumer could
  reasonably have depended on.
- **MINOR** — backward-compatible additions: new subsystem capabilities, new
  optional contract methods with defaults, new plugin hook points.
- **PATCH** — backward-compatible bug fixes with no public contract changes.

**Compatibility guarantees apply only to the public API surface** defined per
ADR-0004 — documented contracts and their exports. Internal modules, private
helpers, and undocumented behavior carry no compatibility promise and may
change in any release, including a PATCH release.

**Pre-1.0 (`0.y.z`).** While the kernel is pre-1.0, breaking changes may
occur in MINOR releases, following standard SemVer pre-1.0 convention — the
public contracts are still being established. The kernel moves to `1.0.0`
only once the subsystem contracts for the full responsibility list in
ADR-0002 are considered stable, a decision to be made explicitly via a future
ADR, not declared unilaterally by a release.

**Deprecation policy (post-1.0):**

- A public contract element slated for incompatible change or removal is
  first marked deprecated in a MINOR release, with a documented migration
  path and a stated removal-target MAJOR version.
- Deprecated elements remain functional — not silently broken or degraded —
  until the stated MAJOR removal.
- Minimum deprecation window is at least one MINOR release cycle before
  removal in the next MAJOR. An exact time-based window (e.g. N months) will
  be set once the kernel has an established release cadence; until then, the
  release-cycle-based minimum is the binding rule.

**Single, unified version.** The kernel is versioned as one package; there is
no independent per-subsystem version number at this stage.

**Every MAJOR and MINOR release is documented** with a changelog, with
breaking changes explicitly called out and linked to the ADR that authorized
them, where applicable.

## Alternatives considered

- **Independent versioning per subsystem** (e.g. `agents` versioned
  separately from `memory`). Rejected for now: adds significant release and
  compatibility-matrix complexity for a single-package kernel with one
  initial consumer. Revisit only if the kernel is ever split into
  independently installable subsystem packages.
- **CalVer or an unversioned "always latest" model.** Rejected: gives
  consuming applications no way to express or reason about compatibility,
  which becomes essential as soon as more than one product depends on the
  kernel.
- **SemVer with breaking changes allowed in MINOR releases even post-1.0.**
  Rejected: undermines the reason to adopt SemVer at all — a MAJOR bump must
  reliably signal "stop and check" for it to be useful to consumers.

## Consequences

- API design under ADR-0004 must keep the public/internal boundary clear,
  since that boundary is exactly what this versioning policy protects.
- Declaring `1.0.0` is a deliberate, ADR-gated milestone, not a judgment call
  made in the course of a routine release.
- Pre-1.0 consumers (initially Mellivor One) should expect breaking changes
  in MINOR bumps until `1.0.0` and should pin versions accordingly.
- The exact time-based deprecation window and release cadence remain open
  and are tracked as future work, not decided by this ADR.
