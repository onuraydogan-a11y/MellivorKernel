# `execution` subsystem spec

Status: Implemented (Sprint 6; authorization wired in Sprint 8; events in
Sprint 9; memory recording in Sprint 11; observability emission in
Sprint 17).

Public contract exported from `mellivor_kernel.execution`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0006](../adr/0006-execution-core-orchestration-layer.md) for why this
subsystem exists,
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
for how it consults authorization without depending on it,
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md) for its
published events,
[ADR-0009](../adr/0009-memory-subsystem-and-execution-recording.md) for
how it records to memory, and
[ADR-0013](../adr/0013-observability-foundation.md) for the observability
foundation it optionally emits structured observations to.

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
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str],
    ) -> AuthorizationOutcome: ...
```

`mellivor_kernel.authorization.AuthorizationEngine` satisfies `Authorizer`
structurally; `execution` never imports `mellivor_kernel.authorization`.
See [ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
and `docs/specs/authorization.md`.

## `execution.events`

Three of `execution`'s own event types (`events.Event` subclasses),
published by `ExecutionEngine`:

- `ExecutionStarted` (`request_id`, `target`, `operation`) — published
  once, at the start of `execute()`.
- `ExecutionCompleted` (adds `execution_time_seconds`) — published when
  the result is successful.
- `ExecutionFailed` (adds `error`, `stage: str | None = None`) — published
  when the result is unsuccessful, whichever stage produced the failure
  (authorization denial, dispatch failure, or an exception during
  execution).

Exactly one of `ExecutionCompleted`/`ExecutionFailed` is published per
`execute()` call, always preceded by `ExecutionStarted`. See ADR-0008 and
`docs/specs/events.md`.

## `ExecutionEngine`

The kernel's single orchestration entry point.

```python
def __init__(
    self,
    dispatcher: Dispatcher,
    *,
    authorizer: Authorizer | None = None,
    event_bus: EventBus | None = None,
    memory: MemoryStore | None = None,
    observability: StructuredEventSink | None = None,
) -> None

def execute(
    self,
    request: ExecutionRequest,
    context: ExecutionContext,
    *,
    granted_permissions: frozenset[str] = frozenset(),
) -> ExecutionResult
```

Flow: `ExecutionRequest -> Authorization -> Dispatcher -> Tool/Provider ->
ExecutionResult`, with `ExecutionStarted`/`ExecutionCompleted`/
`ExecutionFailed` published around it when `event_bus` is configured,
matching `StructuredObservationEvent`s emitted when `observability` is
configured, and each outcome recorded to `memory` when configured.

- Logs the start of execution and publishes `ExecutionStarted`, then emits
  a `"execution.started"` `StructuredObservationEvent` if `observability`
  is configured.
- If `authorizer` is configured, calls
  `authorizer.check(request, context, granted_permissions=granted_permissions)`.
  A denial (`outcome.granted is False`) publishes `ExecutionFailed`
  (`stage="authorization"`) and returns a failed `ExecutionResult`
  immediately (`metadata["stage"] == "authorization"`, `error` from
  `outcome.reason` or a default) **without ever calling `Dispatcher`**.
- If `authorizer` is `None` (the default) or grants, delegates to
  `dispatcher.dispatch(...)` — forwarding `granted_permissions` only when
  a grant was actually produced by an authorizer; with no authorizer
  configured, an empty set is always forwarded, identical to this
  engine's behavior before Sprint 8.
- Logs the outcome (`INFO` on success, `WARNING` on failure), publishes
  `ExecutionCompleted` or `ExecutionFailed` accordingly, then emits the
  matching `"execution.completed"`/`"execution.failed"` structured
  observation if `observability` is configured — always the same
  lifecycle point as the `EventBus` publication, correlated by
  `request.request_id` as the observation's `ObservationContext
  .correlation_id`. The two mechanisms are independent: configuring one
  never affects the other.
- If `memory` is configured, records the outcome as a `MemoryEntry` keyed
  by `request.request_id` (see `docs/specs/memory.md`) — for both success
  and failure, including an authorization denial. A memory backend
  exception is caught and logged, never propagated.
- Returns the result unchanged.

With `event_bus=None` (the default), no events are ever published —
identical to this engine's behavior before Sprint 9. With `memory=None`
(the default), nothing is ever recorded — identical to this engine's
behavior before Sprint 11. With `observability=None` (the default),
nothing is ever emitted — identical to this engine's behavior before
Sprint 17.

Performs no validation of its own beyond what `ExecutionRequest` already
enforces at construction, and no retries or workflow composition — see
ADR-0006/ADR-0007 for why each is explicitly out of scope.

## Dependency relationship

`execution` depends on `core` (the same four types `tools.ToolContext`
depends on), `tools` (`ToolRegistry`, `ToolExecutionPipeline`, `ToolContext`,
`ToolRegistrationError`, `ToolValidationError`, `Permission`), `providers`
(`ProviderRegistry`, `ProviderRegistrationError`) — all three only inside
`dispatch.py` — `events` (`Event`, `EventBus`), `memory`
(`MemoryEntry`, `MemoryStore`), and, as of Sprint 17, `observability`
(`ObservationContext`, `StructuredEventSink`, `StructuredObservationEvent`)
— consumed only through the abstract `StructuredEventSink` Protocol,
never a concrete sink; `observability` itself depends on nothing, so this
adds no new transitive dependency. `core`, `tools`, `providers`, `events`,
`memory`, and `observability` have no dependency on `execution`.
`authorization` depends on `execution` (not the other way around) — see
`docs/specs/authorization.md`.
