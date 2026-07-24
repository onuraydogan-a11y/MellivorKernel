# 0015. Plugin SDK Foundation

Status: Accepted
Date: 2026-07-24

## Context

Sprint 18 (ADR-0014) implemented the Plugin Runtime Foundation:
`Plugin`, `PluginManifest`, `PluginMetadata`, `PluginCapability`,
`PluginContext`, `PluginRegistry`, `PluginLoader`, and `PluginLifecycle`.
That package is deliberately minimal and unopinionated — every field is
validated, but nothing makes constructing a manifest, declaring
capabilities, or implementing the four lifecycle methods convenient. A
plugin author using `mellivor_kernel.plugins` directly must hand-write a
full `PluginManifest(...)` call and implement all four `Plugin` lifecycle
methods even when most of them are no-ops for a given plugin.

This is the same gap `bootstrap.BootstrapBuilder` closed for kernel
composition and `tools.builtin` closed for tool authors: the underlying
contract is correct and stable, but a thin developer-convenience layer on
top of it is what makes the contract pleasant to actually use.

## Decision

Implement the **Plugin SDK Foundation** as a new top-level package,
`mellivor_kernel.plugin_sdk`, exposing exactly:

- **`PluginBuilder`** — a fluent builder (`with_id`, `with_name`,
  `with_version`, `with_author`, `with_description`, `with_capability`,
  `with_capabilities`, `with_minimum_kernel_version`) that accumulates
  field values, then produces either a `PluginManifest`
  (`build_manifest()`) or a `PluginMetadata` (`build_metadata()`) from
  the same state. Performs no validation itself — every field is
  validated only when the underlying `plugins` constructor is called, so
  `PluginValidationError` is raised by, and only by, the Plugin Runtime
  Foundation's own contracts.
- **`BasePlugin`** — a convenience base class implementing `Plugin` with
  no-op default `initialize()`/`start()`/`stop()`/`dispose()`, so a
  concrete plugin overrides only the lifecycle methods it actually needs.
  `metadata` remains abstract; there is no sensible default identity.
- **`create_capability`/`create_manifest`/`create_metadata`** — one-call
  convenience functions forwarding directly to the corresponding `plugins`
  constructor. None of these register anything into a `PluginRegistry` —
  registration remains the caller's own explicit action.
- **`is_valid_capability`/`is_valid_manifest`/`is_valid_metadata`** —
  boolean predicates that attempt the corresponding `plugins` construction
  and catch `PluginValidationError`, rather than re-implementing any
  validation rule. A change to a runtime validation rule in `plugins`
  is automatically reflected here with no SDK code change.

**Dependency boundary.** `plugin_sdk` depends only on `plugins` (and, where
needed, `core`) — never on `execution`, `providers`, `workflow`,
`authorization`, `memory`, `observability`, `security`, or `bootstrap`.
Nothing in the kernel imports `plugin_sdk`; it has no dependents, matching
`plugins` itself.

**Explicitly out of scope**, per this sprint's own instructions: plugin
discovery (filesystem or entry-point), a plugin marketplace, sandboxing,
and any built-in plugin. This sprint is a developer-convenience layer
over the existing runtime, not an expansion of what the runtime does.

## Alternatives considered

- **Add these conveniences directly to `mellivor_kernel.plugins` instead
  of a separate package.** Rejected: `plugins` is the validated contract
  surface itself (ADR-0014); mixing convenience/ergonomic helpers into it
  blurs which parts of the package are "the contract" versus "a nicer way
  to call the contract," the same reason `tools.builtin` is exported
  separately from `tools` rather than folded into it.
- **Re-export `plugins`' own contracts (`Plugin`, `PluginManifest`, etc.)
  from `plugin_sdk` for single-import convenience.** Rejected, matching
  existing precedent: `agents` does not re-export `workflow.WorkflowDefinition`
  even though `AgentDefinition` directly references it — a consumer of
  `plugin_sdk` still imports `mellivor_kernel.plugins` directly for the
  underlying types, keeping each package's `__all__` limited to what it
  actually adds.
- **Have `PluginBuilder`/the `create_*` helpers perform their own
  pre-validation before delegating.** Rejected: this would duplicate
  validation logic already implemented and tested in `plugins`, the exact
  outcome this sprint's scope forbids, and would risk the two validation
  paths drifting out of sync over time.
- **A capability-enforcement mechanism in the SDK.** Rejected: `plugins`
  itself does not enforce capabilities yet (ADR-0014's own "Alternatives
  considered" explicitly deferred a fixed capability vocabulary); the SDK
  cannot enforce a policy the runtime has not defined.

## Consequences

- Plugin authors have a documented, ergonomic path to constructing valid
  manifests/metadata and implementing a minimal plugin, without the SDK
  ever becoming a second source of truth for validation.
- No behavioral change to `plugins`, or to any other existing subsystem:
  `plugin_sdk` has zero dependents and only one dependency edge
  (`plugins`), so this sprint carries zero regression risk.
- Plugin discovery, a marketplace, sandboxing, and any built-in plugin
  remain future work, tracked as open per ADR-0002/ADR-0014 — this ADR
  does not authorize or schedule them.
