# `plugin_sdk` subsystem spec

Status: Foundation (Sprint 19).

Public contract exported from `mellivor_kernel.plugin_sdk`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0015](../adr/0015-plugin-sdk-foundation.md) for why this sprint
exists and what it deliberately excludes (discovery, marketplace,
sandboxing, filesystem loading).

## Scope of this sprint

This spec defines the developer-facing convenience layer over the Plugin
Runtime Foundation (`mellivor_kernel.plugins`,
[ADR-0014](../adr/0014-plugin-runtime-foundation.md)). It does not add any
new validation rule, contract, or capability the runtime does not already
have — every helper here delegates to a `plugins` constructor and lets
that constructor's own `__post_init__` be the sole source of truth for
what is valid. Nothing in this package performs registration; a caller
still constructs and registers a `Plugin` instance into a
`PluginRegistry` explicitly (see `docs/specs/plugins.md`).

## `PluginBuilder`

A fluent builder over `PluginManifest`/`PluginMetadata` construction:

```python
def with_id(self, value: str) -> PluginBuilder
def with_name(self, value: str) -> PluginBuilder
def with_version(self, value: str) -> PluginBuilder
def with_author(self, value: str) -> PluginBuilder
def with_description(self, value: str) -> PluginBuilder
def with_capability(self, name: str, description: str = "") -> PluginBuilder
def with_capabilities(self, *capabilities: PluginCapability) -> PluginBuilder
def with_minimum_kernel_version(self, value: str) -> PluginBuilder

def build_manifest(self) -> PluginManifest
def build_metadata(self) -> PluginMetadata
```

- Every `with_*` method returns the same builder instance, for chaining
  (the same fluent shape `bootstrap.BootstrapBuilder` already uses).
- `with_capability()` adds one capability to the accumulated set;
  `with_capabilities()` replaces the set entirely.
- `with_author()`/`with_minimum_kernel_version()` are consumed only by
  `build_manifest()` — `PluginMetadata` has no corresponding fields, so
  they are silently ignored by `build_metadata()`.
- **No validation happens in the builder itself.** `build_manifest()`/
  `build_metadata()` simply forward the accumulated fields to
  `PluginManifest(...)`/`PluginMetadata(...)`; any invalid field raises
  `PluginValidationError` from that constructor's own `__post_init__`,
  never from `PluginBuilder`.

## `BasePlugin`

A convenience base implementation of `plugins.Plugin`:

```python
class BasePlugin(Plugin):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata: ...

    def initialize(self, context: PluginContext) -> None: ...  # no-op
    def start(self) -> None: ...                                # no-op
    def stop(self) -> None: ...                                  # no-op
    def dispose(self) -> None: ...                               # no-op
```

`metadata` remains abstract — every plugin must declare its own identity,
so there is no sensible default. The four lifecycle methods each default
to a no-op; a concrete subclass overrides only the ones it needs (a
plugin with nothing to release, for example, never overrides
`dispose()`). `BasePlugin` cannot be instantiated directly, nor can a
subclass leaving `metadata` unimplemented (standard `ABC` enforcement).

## Registration helpers (`create_*`)

One-call convenience functions, an alternative to `PluginBuilder` for
callers who do not need the fluent chain:

```python
def create_capability(name: str, description: str = "") -> PluginCapability
def create_manifest(*, id, name, version, author, description="", capabilities=(), minimum_kernel_version="0.0.0") -> PluginManifest
def create_metadata(*, id, name, version, description="", capabilities=()) -> PluginMetadata
```

Each forwards its arguments directly to the corresponding `plugins`
constructor. **None of these registers anything** — no function accepts
or touches a `PluginRegistry`; constructing a `PluginManifest`/
`PluginMetadata`/`PluginCapability` and registering a loaded `Plugin`
instance remain entirely separate, caller-driven steps.

## Validation helpers (`is_valid_*`)

Boolean predicates, useful for a caller that wants to check field values
before committing to construction (for example, validating user input in
a plugin-configuration UI) without catching an exception itself:

```python
def is_valid_capability(name: str, description: str = "") -> bool
def is_valid_metadata(*, id, name, version, description="", capabilities=()) -> bool
def is_valid_manifest(*, id, name, version, author, description="", capabilities=(), minimum_kernel_version="0.0.0") -> bool
```

Each attempts the corresponding `plugins` construction and catches
`PluginValidationError`, returning `False` on failure and `True`
otherwise. **No validation rule is duplicated here** — each predicate is
only as strict (or as lenient) as the `plugins` constructor it wraps. In
particular, `is_valid_metadata()`'s `version` check is blank-only (matching
`PluginMetadata.__post_init__`), while `is_valid_manifest()`'s `version`/
`minimum_kernel_version` checks additionally require `MAJOR.MINOR.PATCH`
format (matching `PluginManifest.__post_init__`) — this asymmetry is
intentional and inherited directly from the runtime, not introduced by
the SDK.

## Dependency relationship

```
plugin_sdk → plugins
```

`plugin_sdk` depends only on `plugins` (and, where a file needs it,
`core` — though no file in this sprint's implementation ends up needing
`core` directly, since everything routes through `plugins`' own already-
`core`-dependent contracts). `plugin_sdk` never depends on `execution`,
`providers`, `workflow`, `authorization`, `memory`, `observability`,
`security`, or `bootstrap`. No other subsystem imports `plugin_sdk` — it
has no dependents, the same position `plugins` itself holds.
