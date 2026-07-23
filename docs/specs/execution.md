# `execution` subsystem spec

Status: Implemented (Sprint 6).

Public contract exported from `mellivor_kernel.execution`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0006](../adr/0006-execution-core-orchestration-layer.md) for why this
subsystem exists and what it deliberately excludes.

## Exceptions

`execution/exceptions.py` — subclasses `core.exceptions.KernelError`, not
the reverse.

- `ExecutionError` — base class for every exception this subsystem raises.
- `ExecutionValidationError` — an invalid `ExecutionRequest` or
  `ExecutionResult`.
- `DispatchError` — `Dispatcher.dispatch()` was given a request whose
  `target` it does not know how to route.

## `ExecutionTarget`

A `StrEnum` naming which subsystem an `ExecutionRequest` should be
dispatched to: `TOOL` (`"tool"`) or `PROVIDER` (`"provider"`). No other
members exist yet — `workflow`/`agents` targets are added only when those
subsystems exist, per ADR-0006.

## `ExecutionRequest`

An immutable (`frozen=True, slots=True`) dataclass carrying only execution
metadata:

```python
target: ExecutionTarget
operation: str
payload: Mapping[str, object] = field(default_factory=dict)
request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

`operation` is the id/name to look up in the target subsystem's own
registry — a tool id for `ExecutionTarget.TOOL`, a provider name for
`ExecutionTarget.PROVIDER`. `request_id` is auto-generated (a UUID4 string)
if not supplied, for log correlation. `__post_init__` rejects a blank
`operation` or `request_id`, raising `ExecutionValidationError`. `target`
membership itself is enforced by the type system, not at construction —
see `Dispatcher` below for what happens if that is bypassed.

Carries **no business state** — a request's payload is opaque to Execution
Core; only the dispatched subsystem interprets it.

## `ExecutionContext`

An immutable (`frozen=True, slots=True`) dataclass, the same four fields as
`tools.ToolContext`, deliberately no more:

```python
configuration: KernelSettings
logger: logging.Logger
runtime: Kernel
services: ServiceContainer
```

Kernel-scoped only, with no knowledge of any specific tool or provider.
`Dispatcher` builds a `ToolContext` from these same fields when dispatching
to the Tool Runtime; `ExecutionContext` itself never imports `tools`.

## `ExecutionResult`

An immutable (`frozen=True, slots=True`) dataclass — the sole
representation of an execution's outcome, structurally identical to
`tools.ToolResult` so it can be produced from one (see `Dispatcher`) without
lossy translation:

```python
success: bool
payload: Mapping[str, object] | None = None
error: str | None = None
execution_time_seconds: float = 0.0
metadata: Mapping[str, object] = field(default_factory=dict)
```

Same invariants as `ToolResult`: `success=False` requires a non-empty
`error`; `success=True` forbids setting `error`; `execution_time_seconds`
must be non-negative. Violating any of these raises
`ExecutionValidationError`.

## `Dispatcher`

The only component in `execution` that imports `tools` or `providers`.

```python
def __init__(
    self,
    tool_registry: ToolRegistry,
    provider_registry: ProviderRegistry,
    *,
    tool_pipeline: ToolExecutionPipeline | None = None,
) -> None

def dispatch(self, request: ExecutionRequest, context: ExecutionContext) -> ExecutionResult
```

- `ExecutionTarget.TOOL` — looks up `request.operation` in `tool_registry`,
  builds a `ToolContext` from `context`'s fields, and runs the tool through
  `tool_pipeline.run(...)`. The resulting `ToolResult` is translated
  field-for-field into an `ExecutionResult`, with `metadata["target"]` set
  to `"tool"` alongside whatever metadata the pipeline itself set (for
  example `"stage"`).
- `ExecutionTarget.PROVIDER` — looks up `request.operation` in
  `provider_registry` and calls `provider.invoke(request.payload)` directly
  (there is no provider-side pipeline to run it through). An exception
  raised by `invoke()` is translated into a failed `ExecutionResult` rather
  than propagated, consistent with ADR-0004's "errors are translated at the
  boundary." `metadata["target"]` is set to `"provider"`.
- An unregistered `operation` in either registry is *not* an exception from
  `dispatch()`'s point of view — the registry's `*RegistrationError` is
  caught and turned into a failed `ExecutionResult`, the same as any other
  execution failure.
- `dispatch()` raises `DispatchError` only if `request.target` is not one
  of the two known members above — unreachable through the type-checked
  public API, but reachable if a caller bypasses static typing (for example
  constructing a request from untrusted external data). This is the one
  case `Dispatcher` cannot represent as a failed `ExecutionResult`, since it
  has no target to attribute the result to.

## `ExecutionEngine`

The kernel's single orchestration entry point.

```python
def __init__(self, dispatcher: Dispatcher) -> None

def execute(self, request: ExecutionRequest, context: ExecutionContext) -> ExecutionResult
```

Logs the start of execution, delegates to `dispatcher.dispatch(...)`, logs
the outcome (`INFO` on success, `WARNING` on failure), and returns the
result unchanged. Performs no validation of its own beyond what
`ExecutionRequest` already enforces at construction, no retries, and no
authorization — see ADR-0006 for why each of those is explicitly out of
scope.

## Dependency relationship

`execution` depends on `core` (the same four types `tools.ToolContext`
depends on), `tools` (`ToolRegistry`, `ToolExecutionPipeline`, `ToolContext`,
`ToolRegistrationError`), and `providers` (`ProviderRegistry`,
`ProviderRegistrationError`) — all three only inside `dispatch.py`. `core`,
`tools`, and `providers` have no dependency on `execution`.
