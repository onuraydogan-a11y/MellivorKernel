# `bootstrap` subsystem spec

Status: Implemented (Sprint 5).

Public contract exported from `mellivor_kernel.bootstrap`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## Why this package exists, and why it isn't inside `core`

`docs/architecture.md` describes `core` as owning "kernel bootstrapping and
lifecycle." That remains true at the level `core` already implements it:
`core.runtime.Kernel` owns the actual startup/shutdown state machine. What
this sprint adds is a *higher* layer — composing `config`, `core`,
`providers`, and `tools` together into one running kernel — and that
composition cannot live inside `core` (or any single subsystem) without
breaking the acyclic dependency graph established in Sprint 2: `core`
depends on nothing else in the package, and `config`/`providers`/`tools`
each depend only on `core`, never on each other. A module that imports all
four necessarily sits *above* them.

`bootstrap` is that layer. It is a new top-level package, a peer to
`core`/`config`/`providers`/`tools`/`agents`/`workflow`/`memory`/`events`/
`plugins` — not a new architectural decision requiring an ADR, since it was
directly commissioned by this sprint and doesn't add a new kernel
*responsibility* per [ADR-0002](../adr/0002-ai-enterprise-kernel-scope-and-subsystems.md);
it only assembles responsibilities that already exist.

**No existing subsystem's code was modified to build this.** `bootstrap`
only consumes the already-public `__all__` of `core`, `config`, `providers`,
and `tools`.

## Exceptions

`bootstrap/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `BootstrapError` — the single exception type for "assembling a kernel
  runtime failed." Any `KernelError` raised during `KernelBootstrap.run`
  (a colliding service registration, the kernel failing to start, etc.) is
  caught and re-raised as `BootstrapError`, with the original chained via
  `__cause__`. This gives callers one exception type to catch for "bootstrap
  failed for any reason," consistent with ADR-0004's "errors are translated
  at the boundary" principle — bootstrap is a boundary.

## `KernelBootstrap`

A stateless orchestrator (a `@staticmethod`, no instance state) implementing
the default bootstrap sequence:

```python
KernelBootstrap.run(
    config: KernelConfig,
    *,
    container: ServiceContainer | None = None,
    provider_registry: ProviderRegistry | None = None,
    tool_registry: ToolRegistry | None = None,
    extra_services: Mapping[type[Any], Any] | None = None,
    register_builtin_tools: bool = False,
) -> RuntimeContext
```

Sequence: create (or accept) a `ServiceContainer`, a `ProviderRegistry`,
and a `ToolRegistry` → optionally register the three built-in demonstration
tools → register the kernel's **default services** into the container
(`KernelConfig`, `ProviderRegistry`, `ToolRegistry` — the only services that
currently exist to register; nothing fictional was invented) → register any
caller-supplied `extra_services` → construct and start the `Kernel` → return
a `RuntimeContext`.

**`register_builtin_tools` defaults to `False`.** The literal ask was
"initialize ToolRegistry," which this reads as "create it, ready to use" —
not "pre-populate it." This mirrors `ProviderRegistry`, which is also
initialized empty (there are no concrete providers to register either).
Auto-registering the demonstration tools is available but opt-in.

## `BootstrapBuilder`

A fluent builder wrapping `KernelBootstrap.run`, for overriding its
defaults:

```python
BootstrapBuilder(config)
    .with_container(container)
    .with_provider_registry(registry)
    .with_tool_registry(registry)
    .with_service(SomeType, some_instance)
    .with_builtin_tools()
    .build() -> RuntimeContext
```

Every `with_*` method returns `self`. `.build()` delegates to
`KernelBootstrap.run` with whatever was accumulated; any `BootstrapError`
raised there propagates unchanged.

## `RuntimeContext`

A read-only view of a bootstrapped runtime, and the **only** object
`KernelBootstrap`/`BootstrapBuilder` return.

```python
.state -> KernelState
.health() -> HealthStatus
.configuration -> KernelSettings
.services -> ServiceContainer
.provider_registry -> ProviderRegistry
.tool_registry -> ToolRegistry
.tool_context(*, logger_name: str = "tools") -> ToolContext
.execution_context(*, logger_name: str = "execution") -> ExecutionContext
```

**Deliberately excluded:** there is no way to retrieve the wrapped `Kernel`
instance, and no `start()` or `shutdown()` method. This satisfies "prevent
direct mutation of Kernel internals" literally — the underlying `Kernel`'s
lifecycle-mutating surface is fully unreachable from a `RuntimeContext`.

**Known gap, left open deliberately:** because there is no `shutdown()`
here, *nothing* returned by this sprint's public API can gracefully stop a
bootstrapped kernel. A consuming application currently has no way to shut
down cleanly through this layer. This was a judgment call between two valid
readings of "read-only" — the conservative one was chosen — and is flagged
here rather than silently resolved either way.

`.services`, `.provider_registry`, and `.tool_registry` remain fully
mutable objects (you can still call `.register(...)` on them through a
`RuntimeContext`) — only the `Kernel`'s own lifecycle is locked down, not
every object reachable from it. Restricting the registries/container too
would defeat their purpose (a DI container and tool/provider registries are
meant to be added to over an application's life).

### Resolving a real integration gap: `ToolContext` needs a `Kernel`

`tools.ToolContext.runtime` requires an actual `core.runtime.Kernel` (per
Sprint 4's contract, unchanged this sprint — see
[Compliance](#compliance-with-this-sprints-constraints) below). A strictly
read-only `RuntimeContext` that never exposes its `Kernel` would make it
*impossible* to construct a valid `ToolContext` from bootstrap output at
all, which would make the whole tool runtime unreachable from a
production-bootstrapped kernel.

`RuntimeContext.tool_context()` resolves this: it is a factory method that
builds a `ToolContext` using `RuntimeContext`'s own *private* `Kernel`
reference — the `Kernel` is used internally to construct the `ToolContext`,
but is never returned to, or reachable by, the caller. `ToolContext` itself
was not changed in any way; this is a new constructor path added entirely
within `bootstrap`.

### The same gap, again: `execution_context()` (Sprint 7)

Sprint 7's Execution Core integration gate hit the identical problem one
level up: `execution.ExecutionContext.runtime` also requires a real
`core.runtime.Kernel`, and there was no supported way to build one from a
bootstrapped `RuntimeContext` — the only alternative would have been
hand-constructing a second `Kernel` outside of bootstrap, defeating the
point of bootstrapping in the first place.

`RuntimeContext.execution_context()` closes it the same way
`tool_context()` did: a factory method using the private `Kernel`
reference internally, added without changing `ExecutionContext` or any
other existing symbol. `bootstrap` now depends on `execution` as well (see
below) — an additive dependency, not a change to any existing contract.

## Dependency relationship

```
bootstrap → core, config, providers, tools, execution
```

`bootstrap` is the only package in the repository that depends on all five.
None of `core`, `config`, `providers`, `tools`, or `execution` depend on
`bootstrap` (and must never — that would be circular). `agents`, `workflow`,
`memory`, `events`, and `plugins` remain untouched, unimplemented, and
unreferenced by `bootstrap`.

## Compliance with this sprint's constraints

- No agents, workflow, memory, or events code was written.
- `providers.BaseProvider` and `tools.BaseTool` (and every other symbol in
  `providers.__all__` / `tools.__all__`) are byte-for-byte unchanged —
  verified via `git diff` against the prior commit before this sprint's
  work began.
- No existing public API was modified. The only new export surface is the
  new `bootstrap` package itself.
