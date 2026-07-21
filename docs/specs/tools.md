# `tools` subsystem spec

Status: Implemented (Sprint 4).

Public contract exported from `mellivor_kernel.tools`. Anything not listed
here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). Built-in demonstration
tools are exported separately from `mellivor_kernel.tools.builtin` — they
are not part of the `tools` subsystem's own contract (see
[Built-in tools](#built-in-tools) below).

## Exceptions

`tools/exceptions.py` — subclasses `core.exceptions.KernelError`, not the
reverse: `core` has no dependency on `tools`.

- `ToolError` — base class for every exception this subsystem raises.
- `ToolRegistrationError` — a registration or lookup failure in
  `ToolRegistry`.
- `ToolValidationError` — an invalid permission identifier, an invalid
  `ToolResult`, or a tool's own `validate()` rejecting its request.

## Permission model

Permissions are **free-form, dotted string identifiers** (`Permission`, an
immutable value object wrapping a validated string), not a closed enum.
Format: lowercase, dot-separated segments of alphanumerics/underscores,
with at least one dot (e.g. `"filesystem.read"`). Invalid formats raise
`ToolValidationError` at construction.

**Deliberate scope note:** the kernel validates permission *format* only,
not a fixed vocabulary of permission *names*. A hypothetical
business-specific permission such as `"crm.read"` is a valid `Permission`
value — the kernel does not reject it — but the kernel never defines it as
a constant, since `crm` is a business domain and the kernel must stay
business-agnostic ([ADR-0003](../adr/0003-repository-boundaries.md)). Only
infrastructure-level permissions are exported as well-known constants:

- `NETWORK_READ` (`"network.read"`)
- `FILESYSTEM_READ` (`"filesystem.read"`)
- `FILESYSTEM_WRITE` (`"filesystem.write"`)
- `PROVIDER_INVOKE` (`"provider.invoke"`)
- `KERNEL_INTERNAL` (`"kernel.internal"`)

`missing_permissions(required, granted) -> frozenset[Permission]` — a pure
function returning the subset of `required` not present in `granted`. Used
internally by `ToolExecutionPipeline`, exported for direct use elsewhere.

## `ToolMetadata`

An immutable (`frozen=True, slots=True`) dataclass: a snapshot of a tool's
static identity — `id`, `name`, `version`, `description`,
`capabilities: frozenset[str]`, `permissions: frozenset[Permission]`.
Produced by `BaseTool.metadata()`; also what `ToolRegistry.enumerate()`
returns (not live tool instances).

## `ToolResult`

An immutable (`frozen=True, slots=True`) dataclass — the sole representation
of a tool execution's outcome:

```python
success: bool
payload: Mapping[str, object] | None = None
error: str | None = None
execution_time_seconds: float = 0.0
metadata: Mapping[str, object] = field(default_factory=dict)
```

`__post_init__` enforces: `success=False` requires a non-empty `error`;
`success=True` forbids setting `error`; `execution_time_seconds` must be
non-negative. Violating any of these raises `ToolValidationError` —
`ToolResult` cannot represent a malformed outcome.

**No exception is ever the "result" of a pipeline run** — see
`ToolExecutionPipeline` below.

## `ToolContext`

An immutable (`frozen=True, slots=True`) dataclass carrying exactly four
fields, deliberately no more:

```python
configuration: KernelSettings   # core.contracts.KernelSettings, not config.KernelConfig
logger: logging.Logger
runtime: Kernel                  # core.runtime.Kernel
services: ServiceContainer       # core.container.ServiceContainer
```

Carries **no business data** — a tool's business-specific input arrives
through the `request` argument to `execute()`, never through the context.
`configuration` is typed against `core`'s `KernelSettings` protocol (not
`config.KernelConfig` directly) purely because `core` already established
that decoupling in Sprint 2; `tools` reuses the same type for consistency,
not because `tools` itself needs to avoid depending on `config` (it simply
never has a reason to).

## `BaseTool` (contract)

An `ABC` — concrete tools subclass it, unlike `core.contracts.KernelSettings`
(a structural `Protocol` used for dependency inversion, not subclassing).

Abstract properties every tool must implement: `id`, `name`, `version`,
`description`, `capabilities: frozenset[str]`,
`permissions: frozenset[Permission]`.

- `.metadata() -> ToolMetadata` — concrete, provided by `BaseTool`; built
  from the abstract properties above. No override needed.
- `.validate(request: Mapping[str, object]) -> None` (abstract) — raises
  `ToolValidationError` if `request` is invalid for this tool; returns
  normally (no return value) if valid.
- `.execute(context: ToolContext, request: Mapping[str, object]) -> ToolResult`
  (abstract) — performs the tool's actual work.

`BaseTool` cannot be instantiated directly, nor can a subclass leaving any
abstract member unimplemented (standard `ABC` enforcement, `TypeError` at
construction).

## `ToolRegistry`

Holds tool instances, keyed by each tool's own `.id`.

- `register(tool)` — raises `ToolRegistrationError` if that id is already
  registered.
- `unregister(tool_id)` — raises `ToolRegistrationError` if not registered.
- `lookup(tool_id) -> BaseTool` — raises `ToolRegistrationError` if not
  registered.
- `exists(tool_id) -> bool`.
- `enumerate() -> tuple[ToolMetadata, ...]` — metadata snapshots, not live
  tool instances, for every registered tool.

## `ToolExecutionPipeline`

Stateless (`run()` takes everything it needs as arguments; no constructor
state). Implements the fixed sequence: **validate → permission check →
execute → result → logging**.

```python
def run(
    self,
    tool: BaseTool,
    context: ToolContext,
    request: Mapping[str, object],
    *,
    granted_permissions: frozenset[Permission] = frozenset(),
) -> ToolResult
```

- Calls `tool.validate(request)`. A `ToolValidationError` becomes a failed
  `ToolResult` (`metadata["stage"] == "validate"`); execution never starts,
  `execution_time_seconds` is `0.0`.
- Computes `missing_permissions(tool.permissions, granted_permissions)`. If
  non-empty, returns a failed `ToolResult`
  (`metadata["stage"] == "permission_check"`,
  `metadata["missing_permissions"]` listing the denied permission strings)
  without calling `execute()`.
- Calls `tool.execute(context, request)`, timing it with
  `time.perf_counter()`. Any exception raised becomes a failed `ToolResult`
  (`metadata["stage"] == "execute"`, `error` set from `str(exception)`).
- On success, the pipeline **overrides** whatever
  `execution_time_seconds` the tool itself set on its returned
  `ToolResult` with its own measured wall-clock time — a tool's
  self-reported timing is never trusted for this field.
- Every outcome is logged via `context.logger` (`INFO` on success,
  `WARNING` on failure, naming the tool and, on failure, the stage) before
  being returned.

**`run()` never raises for a tool-level failure.** It always returns a
`ToolResult`, converting validation errors, permission denials, and
execution exceptions into structured, typed results — this is what "no
exceptions returned as normal results" means in practice.

**Granted permissions are the caller's responsibility.** `ToolContext` does
not carry a permissions field (only the four listed above); whoever calls
`pipeline.run(...)` decides and passes `granted_permissions` explicitly.
This sprint does not implement any authorization/grant-issuing mechanism —
that is left for a future subsystem (likely `agents` or `workflow`) to
decide how granted permissions are determined.

## Built-in tools

`mellivor_kernel.tools.builtin` — exported separately from `tools` itself,
since these are demonstrations, not part of the tool-runtime contract:

- **`EchoTool`** (`id="echo"`) — returns the request payload unchanged.
  No permissions required.
- **`HealthCheckTool`** (`id="health_check"`) — returns
  `context.runtime.health()` as `{healthy, state, detail}`. Requires
  `KERNEL_INTERNAL`.
- **`VersionTool`** (`id="version"`) — returns the installed
  `mellivor_kernel` package version. No permissions required.

None call an external API or touch business data. They exist solely to
exercise the runtime end-to-end (see `tests/test_tool_bootstrap.py`).

## Dependency relationship

`tools` depends only on `core` (`KernelError`, `KernelSettings`, `Kernel`,
`ServiceContainer`) and, for `VersionTool` specifically, the top-level
`mellivor_kernel.version` module. `core` has no dependency on `tools`.
`tools` has no dependency on `config` or `providers`.
