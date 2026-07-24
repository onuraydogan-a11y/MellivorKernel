# 0016. System Information built-in plugin

Status: Accepted
Date: 2026-07-24

## Context

Sprint 18 (ADR-0014) shipped the Plugin Runtime Foundation and Sprint 19
(ADR-0015) shipped the Plugin SDK on top of it — both foundation-only,
with no built-in plugin exercising either end to end. Per CLAUDE.md §13
("Dogfood Principle: No public SDK or extension point is finalized before
internal usage proves the design"), neither package's contract shape has
been proven against a real plugin, only against foundation-level unit
tests using minimal fakes.

`tools` closed the equivalent gap for the Tool Runtime with three
demonstration tools (`EchoTool`, `HealthCheckTool`, `VersionTool`,
Sprint 4) exported separately from `tools` itself, under
`tools.builtin`. The Plugin Runtime and Plugin SDK need the same
treatment: one real plugin, built the way a third-party plugin author
would build one, run through the complete Loader → Registry → Lifecycle
path against a real `Kernel`.

## Decision

Implement exactly one built-in plugin, `SystemInfoPlugin`, in a new
top-level package, `src/mellivor_kernel/plugins_builtin/` — mirroring how
`tools.builtin` is exported separately from `tools`, not folded into
`plugins` or `plugin_sdk` themselves.

`SystemInfoPlugin` exposes read-only kernel information only:

- `kernel_version` — the installed `mellivor_kernel` package version.
- `build_info` — the running Python interpreter and platform, computed
  via the standard library `platform` module; the kernel has no other
  build-metadata concept (no embedded commit sha or build timestamp) to
  report honestly.
- `available_capabilities` — the union of every known plugin's declared
  `PluginCapability` names, read from an optionally supplied
  `PluginRegistry` (falling back to just this plugin's own capabilities
  if none is supplied). Read-only: the plugin never calls `.register()`
  on the registry it is given, only `.enumerate()`.
- `registered_providers`/`registered_tools` — resolved from
  `PluginContext.services` (a `ProviderRegistry`/`ToolRegistry`, if one
  was registered into the container the same way `bootstrap` already
  does via `ServiceContainer.register_instance`), or an empty tuple if
  neither is available. Never mutated.
- `runtime_health` — `PluginContext.runtime.health()`, read-only.

It performs no configuration change and no mutation of any kind, and
demonstrates `BasePlugin`'s "override only when necessary" design
directly: only `metadata` and `initialize()` are overridden; `start()`,
`stop()`, and `dispose()` remain `BasePlugin`'s inherited no-ops, since a
read-only reporting plugin has no active behavior to begin, end, or
resources to release.

**No automatic registration or discovery.** `SystemInfoPlugin` is
constructed, loaded, and registered explicitly by a caller — it does not
register itself, and the kernel does not discover or load it
automatically. `bootstrap` does not compose `plugins_builtin`, matching
every other engine and plugin-runtime package shipped since Sprint 6.

**Dependency footprint.** Unlike `plugins`/`plugin_sdk` (foundation
layers with a strict, ADR-enforced dependency ceiling), `plugins_builtin`
is a leaf consumer, free to depend on whatever it needs to fulfill its
described function — the same latitude `tools.builtin.HealthCheckTool`
already has for `core.runtime.Kernel.health()`. `plugins_builtin` depends
on `plugin_sdk` (for `BasePlugin`), `plugins` (for `PluginContext`,
`PluginMetadata`, `PluginCapability`, `PluginRegistry`,
`PluginLifecycleError`), `providers` (for `ProviderRegistry`, to report
registered providers), `tools` (for `ToolRegistry`, to report registered
tools), `core` (for `HealthStatus`, `ServiceRegistrationError`), and the
top-level `version` module. Nothing depends on `plugins_builtin`.

## Alternatives considered

- **Feed the plugin pre-computed provider/tool name lists at construction
  time instead of resolving `ProviderRegistry`/`ToolRegistry` from the
  service container.** Considered, since it would keep `plugins_builtin`
  dependency-free of `providers`/`tools` entirely. Rejected: this sprint
  is explicitly about dogfooding the *real* runtime path end to end
  (Loader → Registry → Lifecycle against a real `Kernel`), and a plugin
  that only reports what it's handed rather than resolving live registry
  state would demonstrate less of the actual `PluginContext.services`
  resolution channel this plugin is meant to exercise.
- **Have the kernel auto-discover and load `SystemInfoPlugin` at
  bootstrap.** Rejected: explicitly out of this sprint's scope (no
  filesystem/entry-point discovery exists yet, per ADR-0014), and would
  require `bootstrap` to depend on `plugins`/`plugins_builtin`, a
  dependency direction no other engine shipped since Sprint 6 has taken.
- **Multiple built-in plugins in this sprint** (e.g., one per subsystem).
  Rejected: one production-quality plugin, fully exercised end to end, is
  what this sprint's scope calls for; more plugins can follow once this
  one has proven the path, the same incremental approach `tools.builtin`
  took (one tool per sprint slot, not all three at once).

## Consequences

- The Plugin Runtime Foundation and Plugin SDK have now been proven
  against a real, non-trivial plugin — not just foundation-level unit
  tests with minimal fakes — satisfying CLAUDE.md §13 for both.
- No behavioral change to `plugins`, `plugin_sdk`, `providers`, `tools`,
  `core`, or any other existing subsystem: `plugins_builtin` has no
  dependents and its dependencies are all read-only, non-mutating uses of
  already-existing public contracts.
- Plugin discovery, a marketplace, sandboxing, and richer built-in
  plugins remain future work, unchanged from ADR-0014/ADR-0015 — this ADR
  does not authorize or schedule them.
