# `plugins` subsystem spec

Status: Foundation (Sprint 18).

Public contract exported from `mellivor_kernel.plugins`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0014](../adr/0014-plugin-runtime-foundation.md) for why this sprint
exists and what it deliberately excludes (built-in plugins, filesystem or
entry-point discovery).

## Scope of this sprint

This spec defines the runtime primitives a plugin is loaded, validated,
registered, and run through. It does not implement filesystem or
entry-point plugin discovery, a packaging format, sandboxing, or any
built-in plugin — a caller supplies a `PluginManifest` and a
zero-argument constructor callable explicitly, the same shape
`providers.ProviderFactory` already uses for provider types.

## Exceptions

`plugins/exceptions.py` — subclasses `core.exceptions.KernelError`, not
the reverse.

- `PluginError` — base class for every exception this subsystem raises.
- `PluginValidationError` — an invalid `PluginCapability`,
  `PluginMetadata`, or `PluginManifest` value.
- `PluginRegistrationError` — a registration or lookup failure in
  `PluginRegistry`.
- `PluginLoadError` — a `PluginManifest` incompatible with the running
  kernel, a failing constructor, or a plugin whose `metadata.id` does not
  match the manifest it was loaded from.
- `PluginLifecycleError` — an out-of-order `PluginLifecycle` call, or the
  underlying plugin raising during a transition.

## `PluginCapability`

An immutable (`frozen=True, slots=True`) dataclass: `name: str`,
`description: str = ""`. `__post_init__` rejects a blank `name`, raising
`PluginValidationError`. Deliberately free-form — the kernel does not
enumerate a fixed vocabulary of capability kinds, mirroring how
`tools.BaseTool.capabilities` is a plain `frozenset[str]` rather than a
closed enum.

## `PluginMetadata`

An immutable (`frozen=True, slots=True`) dataclass — a snapshot of a
*loaded* plugin instance's self-declared identity, returned by
`Plugin.metadata` and what `PluginRegistry.enumerate()` returns (never
live instances):

```python
id: str
name: str
version: str
description: str
capabilities: frozenset[PluginCapability] = field(default_factory=frozenset)
```

`__post_init__` rejects a blank `id`, `name`, or `version`, raising
`PluginValidationError`.

## `PluginManifest`

An immutable (`frozen=True, slots=True`) dataclass — the load-time
declarative descriptor `PluginLoader.load()` is called with, distinct
from `PluginMetadata`:

```python
id: str
name: str
version: str
description: str
author: str
capabilities: frozenset[PluginCapability] = field(default_factory=frozenset)
minimum_kernel_version: str = "0.0.0"
```

`__post_init__` rejects a blank `id`, `name`, or `author`, and requires
`version`/`minimum_kernel_version` to each be a `MAJOR.MINOR.PATCH`
string (three dot-separated non-negative integers, matching this
kernel's own `__version__` shape per
[ADR-0005](../adr/0005-versioning-strategy.md)) — raising
`PluginValidationError` on any violation. Constructing a manifest never
requires knowing the currently running kernel version; that comparison is
`PluginLoader`'s responsibility, not a structural invariant of the
dataclass itself.

## `PluginContext`

An immutable (`frozen=True, slots=True`) dataclass, the same four fields
as `execution.ExecutionContext` and `tools.ToolContext`, deliberately no
more:

```python
configuration: KernelSettings
logger: logging.Logger
runtime: Kernel
services: ServiceContainer
```

Kernel-scoped only — a plugin receives no business data and no knowledge
of any specific tool, provider, or product feature through this context.
Passed to `Plugin.initialize()` once; a plugin retains whatever it needs
from it.

## `Plugin` (contract)

An `ABC` — concrete plugins subclass it, unlike `core.contracts
.KernelSettings` (a structural `Protocol`, not subclassed).

```python
@property
def metadata(self) -> PluginMetadata: ...


def initialize(self, context: PluginContext) -> None: ...
def start(self) -> None: ...
def stop(self) -> None: ...
def dispose(self) -> None: ...
```

`Plugin` itself enforces nothing about call order — `PluginLifecycle`
(below) is responsible for that. `Plugin` cannot be instantiated directly,
nor can a subclass leaving any abstract member unimplemented (standard
`ABC` enforcement, `TypeError` at construction).

## `PluginLifecycleState`

A `StrEnum`: `REGISTERED`, `INITIALIZED`, `RUNNING`, `STOPPED`,
`DISPOSED`, `FAILED` — mirrors `core.runtime.KernelState`'s role for
`core.runtime.Kernel`.

## `PluginLifecycle`

Wraps one `Plugin` instance and enforces legal state transitions,
starting at `PluginLifecycleState.REGISTERED`:

```python
def __init__(self, plugin: Plugin) -> None

@property
def plugin(self) -> Plugin: ...
@property
def state(self) -> PluginLifecycleState: ...

def initialize(self, context: PluginContext) -> None
def start(self) -> None
def stop(self) -> None
def dispose(self) -> None
```

Legal transitions:

- `initialize()` — only from `REGISTERED` → `INITIALIZED`.
- `start()` — from `INITIALIZED` or `STOPPED` → `RUNNING` (a stopped
  plugin may be restarted).
- `stop()` — only from `RUNNING` → `STOPPED`.
- `dispose()` — from `REGISTERED`, `INITIALIZED`, `STOPPED`, or `FAILED`
  → `DISPOSED`. Idempotent from `DISPOSED` (a no-op, never raises).
  Raises if called from `RUNNING` — a running plugin must be `stop()`ped
  first.

Any call from a state not listed above raises `PluginLifecycleError`
without invoking the underlying plugin. If the underlying `Plugin`
method itself raises, the lifecycle transitions to
`PluginLifecycleState.FAILED` and the original exception is wrapped and
re-raised as `PluginLifecycleError` — mirroring how
`core.runtime.Kernel.start()` transitions to `KernelState.FAILED` and
raises `StartupError` on a startup failure. `FAILED` is not retryable via
`initialize()`/`start()`/`stop()`; `dispose()` remains available from it
for cleanup.

**`PluginLifecycle.plugin` is a cooperative discipline, not an
enforcement boundary (v1.0 scope note, Sprint 25 Public API Freeze
Audit).** `.plugin` returns the wrapped `Plugin` instance directly, and
`PluginRegistry.lookup()` independently returns the same raw instance to
any caller — either path lets code call `Plugin.initialize()`/`.start()`/
`.stop()`/`.dispose()` directly, bypassing this class's state-machine
guard entirely. This is ratified as intentional, stable `1.0.0` scope,
consistent with `plugin_discovery`'s own stated trust model ("a
discovered plugin's code is imported and executed with the same trust as
any other import in the running process"): `PluginLifecycle` exists to
give a *cooperating* caller (such as `ai_engine.AIEngine`) a correctly
sequenced lifecycle, not to prevent a caller who bypasses it from doing
so. No code change results from this ratification.

## `PluginRegistry`

Holds loaded plugin instances, keyed by each plugin's own
`metadata.id`:

- `register(plugin)` — raises `PluginRegistrationError` if that id is
  already registered.
- `unregister(plugin_id)` — raises `PluginRegistrationError` if not
  registered.
- `lookup(plugin_id) -> Plugin` — raises `PluginRegistrationError` if not
  registered.
- `exists(plugin_id) -> bool`.
- `enumerate() -> tuple[PluginMetadata, ...]` — metadata snapshots, not
  live plugin instances, for every registered plugin, in registration
  order.

## `PluginLoader`

```python
def __init__(self, *, kernel_version: str | None = None) -> None

def load(self, manifest: PluginManifest, factory: Callable[[], Plugin]) -> Plugin
```

- `kernel_version` defaults to the installed `mellivor_kernel` package
  version (`mellivor_kernel.version.__version__`).
- `load()` first checks `manifest.minimum_kernel_version` against
  `kernel_version` (parsed as `MAJOR.MINOR.PATCH` tuples); if the
  manifest requires a newer kernel, raises `PluginLoadError` naming the
  plugin id, the required version, and the running version, **without**
  calling `factory`.
- Calls `factory()` to construct the plugin. Any exception `factory`
  raises is caught and re-raised as `PluginLoadError`, consistent with
  ADR-0004's "errors are translated at the boundary."
- Verifies the constructed plugin's `metadata.id` matches `manifest.id`;
  a mismatch raises `PluginLoadError` rather than silently registering an
  inconsistent identity.
- No filesystem path, package name, or entry point is ever read by this
  sprint's `PluginLoader` — `manifest` and `factory` are always supplied
  explicitly by the caller.

## Dependency relationship

```
plugins → core, version
```

`plugins` depends only on `core` (`KernelError`, `KernelSettings`,
`Kernel`, `ServiceContainer`) and the top-level `mellivor_kernel.version`
module (for `PluginLoader`'s default `kernel_version`). No other
subsystem — `providers`, `tools`, `execution`, `authorization`, `events`,
`memory`, `workflow`, `agents`, `security`, `observability` — is imported
by `plugins`, and none of them import `plugins`. `bootstrap` does not
compose `plugins`, matching every engine shipped since Sprint 6; a
consumer wires `PluginRegistry`/`PluginLoader`/`PluginLifecycle`
explicitly.
