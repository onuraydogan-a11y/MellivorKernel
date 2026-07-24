# 0017. Plugin Discovery Foundation

Status: Accepted
Date: 2026-07-25

## Context

Sprint 18 (ADR-0014) explicitly deferred filesystem/entry-point plugin
discovery: "real filesystem or entry-point plugin discovery is a
meaningfully separate concern from the runtime primitives a discovered
plugin would be loaded, validated, registered, and run through —
attempting both at once risks a discovery mechanism built against
runtime contracts that haven't been proven yet." Sprint 20 (ADR-0016)
proved those contracts against a real plugin, `SystemInfoPlugin`, run
through the complete Loader → Registry → Lifecycle path — but every
caller still had to hand-construct a `PluginManifest` and pass a
constructor directly. There has been no way to point the kernel at a
filesystem location and have it find and load plugins on its own.

## Decision

Implement the **Plugin Discovery Foundation** as a new top-level package,
`mellivor_kernel.plugin_discovery`, providing exactly one class,
`PluginDiscovery`, that discovers plugins from a filesystem location and
loads/registers them through the *existing*, unmodified `PluginLoader`
and `PluginRegistry` — introducing no new loading, validation, or
registration logic of its own.

**Discovery convention.** `root` contains one subdirectory per plugin,
each holding a manifest file (default `plugin_manifest.json`, a plain
JSON object) with the same fields `PluginManifest` already defines
(`id`, `name`, `version`, `description`, `author`, `capabilities`,
`minimum_kernel_version`) plus one discovery-only field, `entry_point`
— a `"module.path:AttributeName"` string (the same shape Python's own
packaging `entry_points` convention uses) naming the zero-argument
callable `PluginLoader.load()` calls to construct the `Plugin` instance.
`entry_point` is deliberately not added to `PluginManifest` itself: it is
a *file-format* concept discovery needs to resolve a class from disk,
with no meaning once a plugin is already running — the same reasoning
ADR-0014 used to keep `PluginManifest` and `PluginMetadata` distinct.

`PluginDiscovery` exposes four methods, each doing exactly one step and
composable independently:

- `scan(root)` — lists `root`'s immediate subdirectories containing a
  manifest file, sorted by name for determinism. Read-only; touches
  nothing outside `root`.
- `read_manifest(plugin_dir)` — reads and parses one manifest file into a
  `(PluginManifest, entry_point)` pair. Structural file problems (missing
  file, invalid JSON, missing required keys) raise a new, discovery-only
  exception; an invalid *field value* (blank `id`, malformed `version`)
  raises `PluginValidationError` from `PluginManifest` itself, never
  duplicated here.
- `load(plugin_dir)` — reads the manifest, resolves `entry_point` via
  `importlib`, and calls the *existing* `PluginLoader.load()`. Does not
  register the plugin.
- `discover_and_register(root, registry)` — composes the three methods
  above across every directory `scan()` finds, registering each loaded
  plugin into the caller's `PluginRegistry` in discovery order. Fails
  fast: the first error aborts discovery, and plugins already registered
  before that point remain registered (no rollback, the same
  no-transaction semantics `PluginRegistry` itself already has).

**New exceptions**, all subclassing `core.exceptions.KernelError`
directly (never `plugins.exceptions.PluginError`, matching every other
subsystem's rule that exception hierarchies do not cross package
boundaries): `PluginDiscoveryError` (base), `ManifestNotFoundError`,
`ManifestParseError`, `EntryPointError`. `PluginValidationError`,
`PluginLoadError`, and `PluginRegistrationError` — all already defined in
`plugins` — propagate unwrapped for the failure modes `plugins` already
owns.

**Dependency boundary.** `plugin_discovery` depends only on `plugins`
and `core` — never on `providers`, `tools`, `execution`, `authorization`,
`events`, `memory`, `workflow`, `agents`, `security`, `observability`,
`bootstrap`, `plugin_sdk`, or `plugins_builtin`. Nothing in the kernel
imports `plugin_discovery`; it has no dependents, the same position
`plugins` and `plugin_sdk` each hold. `bootstrap` does not compose it,
consistent with every plugin-runtime package shipped since Sprint 18.

**Explicitly out of scope**, per this sprint's own instructions: a
plugin marketplace, remote plugins, sandboxing, hot reload, signature
verification, and package installation. A discovered plugin's code is
imported and executed with exactly the same trust as any other import in
the running process — this sprint does not add, and does not claim to
add, any isolation or verification boundary around that.

## Alternatives considered

- **A single manifest file listing every plugin, instead of one
  directory per plugin.** Rejected: one-directory-per-plugin lets a
  plugin's manifest live alongside its own code (or be entirely separate
  from it, since `entry_point` can name any importable module) without a
  central file every plugin author has to edit — the same
  self-contained-unit shape `tools.builtin`'s and `plugins_builtin`'s own
  packages already have.
- **Add `entry_point` to `PluginManifest` itself.** Rejected: `plugins`
  is the validated runtime contract (ADR-0014); a discovery-specific,
  file-format-only field has no meaning to a live `Plugin` instance and
  would force every non-filesystem caller (e.g. `PluginBuilder`,
  `create_manifest`) to carry a field they never use — the identical
  reasoning ADR-0014 used to keep `PluginManifest` and `PluginMetadata`
  separate.
- **TOML instead of JSON for the manifest file format.** Considered,
  since `pyproject.toml` is TOML and Python 3.12+ ships `tomllib` in the
  standard library. Rejected in favor of JSON: no new stdlib dependency
  either way, and JSON is the more common plugin-manifest convention in
  comparable ecosystems (npm's `package.json`, VS Code's extension
  manifest) with a simpler, less ambiguous grammar for this narrow use.
- **Best-effort discovery that skips a broken plugin directory and
  continues.** Rejected for this foundation: silently skipping a
  misconfigured plugin risks masking a real authoring mistake, and this
  sprint explicitly excludes sandboxing/signature verification, so
  failing loudly and immediately is the safer default. A best-effort mode
  can be layered on top later without changing today's contract.
- **Reuse `plugins.exceptions.PluginError` as the base for the new
  exceptions.** Rejected: every existing subsystem's exception hierarchy
  subclasses `core.exceptions.KernelError` directly, never a sibling
  subsystem's base, specifically to avoid coupling exception hierarchies
  across package boundaries. `plugin_discovery` follows that rule exactly.

## Consequences

- A caller can now point the kernel at a filesystem location and have
  every well-formed plugin under it discovered, validated, loaded, and
  registered without hand-writing a `PluginManifest` or constructor call
  per plugin — closing the last piece of "Plugin loading" this sprint's
  scope covers.
- No behavioral change to `plugins`, `plugin_sdk`, `plugins_builtin`, or
  any other existing subsystem: `plugin_discovery` has zero dependents
  and its only dependency edge beyond `core` is `plugins`, unmodified.
- A plugin marketplace, remote plugins, sandboxing, hot reload, signature
  verification, and package installation remain future work, tracked as
  open per ADR-0002/ADR-0014/ADR-0016 — this ADR does not authorize or
  schedule them.
