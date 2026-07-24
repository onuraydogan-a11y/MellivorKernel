# `plugins_builtin` subsystem spec

Status: Foundation (Sprint 20) — exactly one built-in plugin.

Public contract exported from `mellivor_kernel.plugins_builtin`. Anything
not listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0016](../adr/0016-system-info-built-in-plugin.md) for why this
sprint exists.

## Scope of this sprint

Exactly one built-in plugin, `SystemInfoPlugin`, demonstrating the Plugin
Runtime Foundation (`plugins`,
[ADR-0014](../adr/0014-plugin-runtime-foundation.md)) and the Plugin SDK
(`plugin_sdk`,
[ADR-0015](../adr/0015-plugin-sdk-foundation.md)) end to end, built the
way a third-party plugin author would build one. No plugin discovery, no
marketplace, no sandboxing, and no automatic registration or bootstrap
composition — a caller constructs, loads, registers, and drives this
plugin explicitly, the same as any other plugin.

## `SystemInfoSnapshot`

An immutable (`frozen=True, slots=True`) dataclass — the read-only
result of `SystemInfoPlugin.collect()`:

```python
kernel_version: str
build_info: str
available_capabilities: frozenset[str]
registered_providers: tuple[str, ...]
registered_tools: tuple[str, ...]
runtime_health: HealthStatus
```

- `kernel_version` — `mellivor_kernel.version.__version__`.
- `build_info` — `"Python {platform.python_version()} on {platform.system()} {platform.release()}"`.
  The kernel has no other build-metadata concept (no embedded commit sha
  or build timestamp) to report.
- `available_capabilities` — the union of `PluginCapability.name` across
  every plugin known to the `PluginRegistry` this plugin was constructed
  with, or just this plugin's own capabilities if none was supplied.
- `registered_providers` — every name in the `ProviderRegistry` resolved
  from `PluginContext.services`, or `()` if none is registered there.
- `registered_tools` — every id in the `ToolRegistry` resolved from
  `PluginContext.services`, or `()` if none is registered there.
- `runtime_health` — `PluginContext.runtime.health()`.

## `SystemInfoPlugin`

```python
class SystemInfoPlugin(BasePlugin):
    def __init__(self, *, plugin_registry: PluginRegistry | None = None) -> None

    @property
    def metadata(self) -> PluginMetadata: ...  # id="system-info"

    def initialize(self, context: PluginContext) -> None: ...  # retains context
    # start(), stop(), dispose(): inherited BasePlugin no-ops -- never overridden

    def collect(self) -> SystemInfoSnapshot: ...
```

- `metadata.id` is always `"system-info"`; `metadata.capabilities`
  always includes a `"kernel.introspection"` capability.
- `initialize(context)` only retains `context` for `collect()` — it
  performs no other setup, no configuration change, and no mutation.
- `collect()` raises `PluginLifecycleError` if called before
  `initialize()`. It may be called at any point after that — including
  before `start()` — since `start()` is a no-op for this plugin; there is
  no "not yet running" state that would make `collect()`'s data
  incomplete.
- `_resolve_provider_names()`/`_resolve_tool_ids()` catch
  `ServiceRegistrationError` from `ServiceContainer.resolve()` and
  degrade to `()` rather than raising — a `PluginContext` built without a
  registered `ProviderRegistry`/`ToolRegistry` is a valid, supported
  configuration, not an error.

## Constructing and running `SystemInfoPlugin` (the real path)

There is no `RuntimeContext.plugin_context()` builder — `bootstrap` does
not depend on `plugins` (unchanged since ADR-0014), and `RuntimeContext`
never exposes the `Kernel` it wraps. A caller builds `PluginContext`
directly, registering `ProviderRegistry`/`ToolRegistry` into its
`ServiceContainer` the same way
`bootstrap.KernelBootstrap._register_default_services` already does:

```python
kernel = Kernel(settings)
kernel.start()

services = ServiceContainer()
services.register_instance(ProviderRegistry, provider_registry)
services.register_instance(ToolRegistry, tool_registry)

context = PluginContext(
    configuration=settings, logger=get_logger("..."), runtime=kernel, services=services,
)

manifest = PluginBuilder().with_id("system-info")...build_manifest()
plugin = PluginLoader(kernel_version=__version__).load(manifest, SystemInfoPlugin)

registry = PluginRegistry()
registry.register(plugin)

lifecycle = PluginLifecycle(plugin)
lifecycle.initialize(context)
lifecycle.start()
snapshot = plugin.collect()
lifecycle.stop()
lifecycle.dispose()
```

See [`examples/plugin_system_info.py`](../../examples/plugin_system_info.py)
for the complete, runnable version of this sequence, and
`tests/test_builtin_plugin_integration.py` for the same sequence
exercised as pytest assertions.

## Dependency relationship

```
plugins_builtin → core, plugin_sdk, plugins, providers, tools, version
```

Unlike `plugins`/`plugin_sdk`, `plugins_builtin` carries no dependency
ceiling of its own — it depends on whatever it needs to fulfill
`SystemInfoPlugin`'s described function, the same latitude
`tools.builtin` already has. Nothing depends on `plugins_builtin`.
