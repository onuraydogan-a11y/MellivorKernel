# 0014. Plugin Runtime Foundation

Status: Accepted
Date: 2026-07-24

## Context

ADR-0002 names **Plugin loading** as a fixed kernel responsibility — the
extension point through which a consuming application adds behavior the
kernel does not natively provide, never by forking or monkey-patching
kernel internals (ADR-0004 §"Plugins"). It has been the last
fully-unimplemented responsibility on that list: `src/mellivor_kernel/plugins/`
has existed since Sprint 1 as an empty package skeleton, deliberately
deferred past every re-sequencing decision from Sprint 6 onward in favor of
subsystems the rest of the kernel could build on immediately (see
`docs/architecture/roadmap.md`).

A future `1.0.0` release cannot responsibly claim every ADR-0002
responsibility is stable while `plugins` has no implementation at all. At
the same time, real filesystem or entry-point plugin discovery is a
meaningfully separate concern from the runtime primitives a discovered
plugin would be loaded, validated, registered, and run through — attempting
both at once risks a discovery mechanism built against runtime contracts
that haven't been proven yet.

## Decision

Implement the **Plugin Runtime Foundation**: the contracts, manifest model,
registry, loader, and lifecycle state management a plugin is loaded and run
through — with **no built-in plugins** and **no filesystem or entry-point
discovery** at this sprint's scope. A caller supplies an explicit
`PluginManifest` and a zero-argument constructor callable directly, the
same explicit-registration shape `providers.ProviderFactory` already uses
for provider types.

The package provides:

- **Contracts** — `Plugin` (an `ABC` every plugin implements), `PluginMetadata`
  (a loaded instance's self-declared identity snapshot), `PluginContext`
  (the kernel-scoped state a plugin receives at `initialize()`), and
  `PluginCapability` (a free-form, named capability a plugin declares).
- **`PluginManifest`** — an immutable, validated declarative descriptor
  (`id`, `name`, `version`, `description`, `author`, `capabilities`,
  `minimum_kernel_version`), the input `PluginLoader.load()` is called
  with. Distinct from `PluginMetadata`: the manifest is the load-time
  "package declaration," including a compatibility gate
  (`minimum_kernel_version`) irrelevant to a plugin once it is running.
- **`PluginRegistry`** — registers, looks up, enumerates, and prevents
  duplicate registration of loaded `Plugin` instances, keyed by
  `metadata.id`, mirroring `tools.ToolRegistry`/`providers.ProviderRegistry`
  exactly.
- **`PluginLoader`** — validates a manifest's `minimum_kernel_version`
  against the running kernel, instantiates the plugin via the supplied
  factory, and translates both an incompatible version and a failing
  constructor into a single `PluginLoadError` at the boundary (ADR-0004).
- **`PluginLifecycle`** — a small state machine (`PluginLifecycleState`:
  `REGISTERED` → `INITIALIZED` → `RUNNING` ⇄ `STOPPED` → `DISPOSED`, with
  `FAILED` on any underlying exception) enforcing legal
  `initialize()`/`start()`/`stop()`/`dispose()` call order for one `Plugin`
  instance, mirroring `core.runtime.Kernel`'s own guarded `start()`/
  `shutdown()` sequence.

**Dependency boundary.** `plugins` depends only on `core` (`KernelSettings`,
`Kernel`, `ServiceContainer`, `KernelError`) and the top-level `version`
module (for the loader's default kernel-version comparison) — never on
`providers`, `tools`, `execution`, `authorization`, `events`, `memory`,
`workflow`, `agents`, `security`, or `observability`. No subsystem imports
`plugins`, and `bootstrap` does not compose it, matching the existing
pattern for every engine shipped after Sprint 5.

## Alternatives considered

- **Implement filesystem/entry-point discovery in the same sprint.**
  Rejected: discovery is a separate, larger concern (trust boundaries,
  packaging format, install location) that should be designed against a
  proven runtime, not simultaneously with it — the same reasoning that kept
  `execution` (Sprint 6) and `authorization` (Sprint 8) as separate sprints
  from their later validation gates.
- **A single `PluginMetadata`/manifest type instead of two.** Rejected:
  conflating the load-time descriptor (which needs `author` and
  `minimum_kernel_version`, and exists before any instance does) with the
  runtime self-report a live instance exposes (which never needs
  `minimum_kernel_version` again once compatibility was already checked)
  would force every `PluginMetadata` consumer to carry fields with no
  post-load meaning.
- **Ship a template-method `Plugin` base class that owns its own lifecycle
  state.** Rejected in favor of a separate `PluginLifecycle` wrapper: this
  keeps `Plugin` a minimal interface plugin authors implement, while state
  enforcement lives in one reusable place — the same separation
  `core.runtime.Kernel` already models for the kernel's own lifecycle.
- **A fixed enum of capability kinds for `PluginCapability`.** Rejected:
  the kernel has no basis yet for what capability categories a real plugin
  needs (no built-in plugin exists to observe), and inventing one now risks
  the same premature-vocabulary mistake `tools.Permission` deliberately
  avoided by staying a validated free-form string rather than a closed enum.

## Consequences

- `plugins` is no longer an empty skeleton; it is a genuine foundation
  package with contracts, tests, and a spec, the same status `security`
  (ADR-0012) and `observability` (ADR-0013) reached in Sprints 15–16.
- No subsystem's existing behavior changes: `plugins` has no dependents and
  depends on nothing beyond `core`/`version`, so this sprint carries zero
  regression risk to `execution`, `authorization`, `workflow`, `agents`,
  `security`, or `observability`.
- Filesystem discovery, a concrete plugin packaging format, sandboxing, and
  any built-in plugin remain future work, tracked as open per ADR-0002 —
  this ADR does not authorize or schedule them.
- `bootstrap` still does not compose `plugins` automatically, consistent
  with every engine shipped since Sprint 6; a consumer wires
  `PluginRegistry`/`PluginLoader`/`PluginLifecycle` explicitly.
