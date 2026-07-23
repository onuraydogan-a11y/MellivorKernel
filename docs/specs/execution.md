# `execution` subsystem spec

Status: Implemented (Sprint 6; authorization wired in Sprint 8).

Public contract exported from `mellivor_kernel.execution`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0006](../adr/0006-execution-core-orchestration-layer.md) for why this
subsystem exists, and
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
for how it consults authorization without depending on it.

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

def dispatch(
    self,
    request: ExecutionRequest,
    context: ExecutionContext,
    *,
    granted_permissions: frozenset[str] = frozenset(),
) -> ExecutionResult
```

- `ExecutionTarget.TOOL` — looks up `request.operation` in `tool_registry`,
  builds a `ToolContext` from `context`'s fields, converts each raw string
  in `granted_permissions` into a `tools.permissions.Permission` (an
  invalid format is translated into a failed `ExecutionResult`,
  `metadata["stage"] == "permission_check"`, rather than raised), and runs
  the tool through `tool_pipeline.run(..., granted_permissions=...)`. The
  resulting `ToolResult` is translated field-for-field into an
  `ExecutionResult`, with `metadata["target"]` set to `"tool"` alongside
  whatever metadata the pipeline itself set (for example `"stage"`).
- `ExecutionTarget.PROVIDER` — looks up `request.operation` in
  `provider_registry` and calls `provider.invoke(request.payload)` directly
  (there is no provider-side pipeline to run it through). `granted_permissions`
  is ignored on this path — `BaseProvider` has no permission model to
  check it against. An exception raised by `invoke()` is translated into a
  failed `ExecutionResult` rather than propagated, consistent with
  ADR-0004's "errors are translated at the boundary." `metadata["target"]`
  is set to `"provider"`.
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

## `execution.contracts`: the authorization seam

Two small `Protocol`s (`@runtime_checkable`), the same dependency-inversion
pattern `core.contracts.KernelSettings` established in Sprint 2 — reused
here rather than `execution` importing `authorization` directly:

```python
class AuthorizationOutcome(Protocol):
    granted: bool
    reason: str | None

class Authorizer(Protocol):
    def check(
        self, request: ExecutionRequest, context: ExecutionContext,
        *, granted_permissions: frozenset[str],
    ) -> AuthorizationOutcome: ...
```

`mellivor_kernel.authorization.AuthorizationEngine` satisfies `Authorizer`
structurally; `execution` never imports `mellivor_kernel.authorization`.
See [ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
and `docs/specs/authorization.md`.

## `ExecutionEngine`

The kernel's single orchestration entry point.

```python
def __init__(self, dispatcher: Dispatcher, *, authorizer: Authorizer | None = None) -> None

def execute(
    self,
    request: ExecutionRequest,
    context: ExecutionContext,
    *,
    granted_permissions: frozenset[str] = frozenset(),
) -> ExecutionResult
```

Flow: `ExecutionRequest -> Authorization -> Dispatcher -> Tool/Provider ->
ExecutionResult`.

- Logs the start of execution.
- If `authorizer` is configured, calls
  `authorizer.check(request, context, granted_permissions=granted_permissions)`.
  A denial (`outcome.granted is False`) returns a failed `ExecutionResult`
  immediately (`metadata["stage"] == "authorization"`, `error` from
  `outcome.reason` or a default) **without ever calling `Dispatcher`**.
- If `authorizer` is `None` (the default) or grants, delegates to
  `dispatcher.dispatch(...)` — forwarding `granted_permissions` only when
  a grant was actually produced by an authorizer; with no authorizer
  configured, an empty set is always forwarded, identical to this
  engine's behavior before Sprint 8.
- Logs the outcome (`INFO` on success, `WARNING` on failure) and returns
  the result unchanged.

Performs no validation of its own beyond what `ExecutionRequest` already
enforces at construction, and no retries or workflow composition — see
ADR-0006/ADR-0007 for why each is explicitly out of scope.

## Dependency relationship

`execution` depends on `core` (the same four types `tools.ToolContext`
depends on), `tools` (`ToolRegistry`, `ToolExecutionPipeline`, `ToolContext`,
`ToolRegistrationError`, `ToolValidationError`, `Permission`), and
`providers` (`ProviderRegistry`, `ProviderRegistrationError`) — all three
only inside `dispatch.py`. `core`, `tools`, and `providers` have no
dependency on `execution`. `authorization` depends on `execution` (not the
other way around) — see `docs/specs/authorization.md`.
