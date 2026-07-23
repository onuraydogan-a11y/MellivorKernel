# `events` subsystem spec

Status: Implemented (Sprint 9).

Public contract exported from `mellivor_kernel.events`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md) for why this
subsystem exists and what it deliberately excludes (a distributed
messaging system, metrics, tracing, audit logging).

## Exceptions

`events/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `EventDispatchError` — the only exception this subsystem raises, and
  only for misuse of the bus API itself (unsubscribing a registration that
  is not, or is no longer, active). Never raised for a handler's own
  exception during `publish()` — see `InMemoryEventBus` below.

## `Event`

An immutable (`frozen=True, slots=True, kw_only=True`) dataclass — the
base type every concrete event derives from:

```python
event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

Declared `kw_only` so a subclass can add its own required, non-default
fields (for example `execution.events.ExecutionStarted.request_id`)
without a dataclass field-ordering conflict — Python moves `kw_only`
fields to the end of the generated `__init__` regardless of declaration
order, so a base class's defaulted `kw_only` fields never force a
subclass's required fields to also default.

`events` defines no concrete event types of its own — `ExecutionStarted`,
`ExecutionCompleted`, `ExecutionFailed` (`execution.events`) and
`AuthorizationGranted`, `AuthorizationDenied` (`authorization.events`) are
each owned by the subsystem that publishes them. `events` stays free of
any knowledge of "execution," "authorization," "tools," or "providers,"
so it remains reusable by any future subsystem without modification.

## `EventHandler`

A `@runtime_checkable` `Protocol`:

```python
def handle(self, event: Event) -> None: ...
```

Anything with a matching `handle()` method satisfies this structurally —
no base class to subclass, matching the same seam pattern as
`core.contracts.KernelSettings`.

## `EventRegistration`

An immutable (`frozen=True, slots=True`) dataclass — an opaque handle:

```python
event_type: type[Event]
registration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

Returned by `subscribe()`, required by `unsubscribe()`. Carries no
reference to the handler itself; a bus implementation looks the
subscription up however it stores things internally.

## `EventBus`

A `@runtime_checkable` `Protocol` — the contract every bus implementation
satisfies:

```python
def publish(self, event: Event) -> None
def subscribe(self, event_type: type[Event], handler: EventHandler) -> EventRegistration
def unsubscribe(self, registration: EventRegistration) -> None
```

Publishers (`execution.ExecutionEngine`, `authorization.AuthorizationEngine`)
depend on this Protocol only, never on `InMemoryEventBus` concretely — the
seam a future distributed implementation (Kafka, NATS, Redis) plugs into
without either publisher changing.

## `InMemoryEventBus`

The only concrete `EventBus` implementation this sprint adds. Not a
distributed messaging system: synchronous, in-process, no persistence, no
cross-process delivery.

- `subscribe(event_type, handler)` — always succeeds; the same handler may
  be subscribed more than once (no deduplication), and multiple different
  handlers may subscribe to the same `event_type`.
- `publish(event)` — dispatches to every handler subscribed to
  `type(event)` **exactly** (no subscription to a base class receives
  subtype events), in subscription order. A handler's own exception is
  caught and logged (`WARNING`, via a `"events"`-namespaced logger) and
  does not stop delivery to the remaining handlers, and never propagates
  to the caller that published the event. Publishing an event with zero
  subscribers is a silent no-op.
- `unsubscribe(registration)` — raises `EventDispatchError` if
  `registration` does not name an active subscription on this bus
  instance (already removed, or issued by a different bus).

## Integration: `execution` and `authorization`

Both `ExecutionEngine.__init__` and `AuthorizationEngine.__init__` gained
an optional `event_bus: EventBus | None = None` parameter in this sprint.
With no bus configured, neither engine's behavior differs at all from
before this sprint.

- `ExecutionEngine.execute()` publishes `execution.events.ExecutionStarted`
  at the start, then exactly one of `ExecutionCompleted` or
  `ExecutionFailed` before returning — `ExecutionFailed` fires whether the
  failure came from an authorization denial or a dispatch failure, uniform
  regardless of stage.
- `AuthorizationEngine.check()` — not `authorize()` — publishes
  `authorization.events.AuthorizationGranted` or `AuthorizationDenied`.
  `authorize()` is a pure decision function with no execution request id
  to correlate events against, so it never publishes; `check()` has one
  (`ExecutionRequest.request_id`) and is the method `ExecutionEngine`
  actually calls, so every published event — from either subsystem —
  carries the same `request_id` for cross-subsystem correlation.

See `docs/specs/execution.md` and `docs/specs/authorization.md` for each
engine's full contract.

## Dependency relationship

```
execution → events
authorization → events
```

`events` depends on `core` only (`KernelError`, `get_logger`) and has no
dependency on `execution`, `authorization`, `tools`, or `providers`. This
is a normal dependency on generic infrastructure, not the kind of coupling
ADR-0007 inverted away from for `authorization` — `events` contains no
decision logic for `execution` to stay ignorant of, unlike an
authorization policy.
