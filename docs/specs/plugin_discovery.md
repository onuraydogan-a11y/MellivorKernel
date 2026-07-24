# `plugin_discovery` subsystem spec

Status: Foundation (Sprint 21).

Public contract exported from `mellivor_kernel.plugin_discovery`.
Anything not listed here is internal and carries no compatibility
guarantee, per [ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0017](../adr/0017-plugin-discovery-foundation.md) for why this
sprint exists and what it deliberately excludes (marketplace, remote
plugins, sandboxing, hot reload, signature verification, package
installation).

## Scope of this sprint

This spec defines discovery of plugins from a filesystem location, and
their loading/registration through the *existing*, unmodified
`PluginLoader`/`PluginRegistry` (`mellivor_kernel.plugins`,
[ADR-0014](../adr/0014-plugin-runtime-foundation.md)). It introduces no
new loading, validation, or registration logic — every manifest field
value is validated only by `PluginManifest`/`PluginCapability`
themselves, and every load/registration decision is made only by
`PluginLoader`/`PluginRegistry` themselves.

## Manifest file format

A plugin directory contains one manifest file (default filename
`plugin_manifest.json`, overridable per `PluginDiscovery` instance) — a
JSON object with the same fields `PluginManifest` already defines, plus
one discovery-only field:

```json
{
  "id": "example",
  "name": "Example Plugin",
  "version": "1.0.0",
  "description": "An example plugin.",
  "author": "Someone",
  "minimum_kernel_version": "0.13.0",
  "capabilities": [
    {"name": "kernel.introspection", "description": "Read-only info."}
  ],
  "entry_point": "package.module:PluginClass"
}
```

- `id`, `name`, `version`, `author` are **required**; their absence
  raises `ManifestParseError` (a structural, file-format problem).
  `description`, `capabilities`, `minimum_kernel_version` are optional,
  defaulting exactly as `PluginManifest` itself defaults them (`""`,
  `frozenset()`, `"0.0.0"`).
- Once all required keys are present, each field's *value* is validated
  only by `PluginManifest.__post_init__`/`PluginCapability.__post_init__`
  — a blank `id` or a malformed `version` raises `PluginValidationError`,
  never a discovery-specific error.
- `entry_point` is **required** and discovery-only: a
  `"module.path:AttributeName"` string (the same shape Python's own
  packaging `entry_points` convention uses) naming the zero-argument
  callable `PluginLoader.load()` calls to construct the `Plugin`
  instance. It is never part of `PluginManifest` itself — the file
  format layers it on top, the same separation ADR-0014 already
  established between `PluginManifest` (load-time descriptor) and
  `PluginMetadata` (runtime self-report).

## Exceptions

`plugin_discovery/exceptions.py` — subclasses `core.exceptions
.KernelError` directly, not `plugins.exceptions.PluginError` (matching
every existing subsystem's rule that exception hierarchies never cross
package boundaries).

- `PluginDiscoveryError` — base class for every exception this subsystem
  raises.
- `ManifestNotFoundError` — a candidate plugin directory has no manifest
  file.
- `ManifestParseError` — the manifest file exists but is not valid JSON,
  is not a JSON object, is missing a required field, or has a malformed
  `capabilities` entry.
- `EntryPointError` — the `entry_point` string is not in
  `module:attribute` format, its module cannot be imported, its
  attribute does not exist, or the resolved attribute is not callable.

`plugins.exceptions.PluginValidationError`, `PluginLoadError`, and
`PluginRegistrationError` all propagate unwrapped from the methods
below — this subsystem never re-wraps a `plugins` exception into one of
its own.

## `PluginDiscovery`

```python
DEFAULT_MANIFEST_FILENAME = "plugin_manifest.json"

class PluginDiscovery:
    def __init__(
        self, loader: PluginLoader | None = None, *, manifest_filename: str = DEFAULT_MANIFEST_FILENAME
    ) -> None

    def scan(self, root: Path | str) -> tuple[Path, ...]
    def read_manifest(self, plugin_dir: Path | str) -> tuple[PluginManifest, str]
    def load(self, plugin_dir: Path | str) -> Plugin
    def discover_and_register(self, root: Path | str, registry: PluginRegistry) -> tuple[Plugin, ...]
```

- `loader` defaults to a new `PluginLoader()` (kernel version taken from
  the installed package) — the same default `PluginLoader` itself uses.
- `scan(root)` — returns `root`'s immediate subdirectories that contain
  a manifest file, sorted by name for determinism. Raises
  `PluginDiscoveryError` if `root` is not a directory. Read-only: never
  reads a manifest file's contents, only checks for its existence.
- `read_manifest(plugin_dir)` — reads and parses the manifest file in
  `plugin_dir`. Returns `(manifest, entry_point)`. Does not resolve the
  entry point (no import side effect).
- `load(plugin_dir)` — calls `read_manifest`, resolves `entry_point` via
  `importlib`, and calls `PluginLoader.load(manifest, factory)`. Does
  **not** register the plugin into any registry.
- `discover_and_register(root, registry)` — calls `scan(root)`, then
  `load()` and `registry.register()` for each directory found, in
  order. **Fails fast**: the first exception aborts discovery
  immediately; plugins already registered before that point remain
  registered — this method never rolls back a partially completed
  discovery, matching `PluginRegistry`'s own lack of transactions.
  Returns the discovered plugins in discovery order.

## Dependency relationship

```
plugin_discovery → core, plugins
```

`plugin_discovery` depends only on `plugins` (`Plugin`, `PluginManifest`,
`PluginCapability`, `PluginLoader`, `PluginRegistry`, and their
exceptions) and `core` (`KernelError`). It never depends on `providers`,
`tools`, `execution`, `authorization`, `events`, `memory`, `workflow`,
`agents`, `security`, `observability`, `bootstrap`, `plugin_sdk`, or
`plugins_builtin`. No other subsystem imports `plugin_discovery` — it
has no dependents, the same position `plugins` and `plugin_sdk` each
hold.
