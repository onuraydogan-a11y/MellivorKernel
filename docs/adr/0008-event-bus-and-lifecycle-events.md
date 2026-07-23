# 0008. Event Bus, and lifecycle events published by Execution and Authorization

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names the
**Event bus** as a fixed kernel responsibility with a reserved package
(`events/`) but no implementation. The roadmap has recommended it for a
sprint slot three times running (Sprints 6, 7, 8), each time superseded by
higher-priority work (Execution Core, its integration gate, then
Authorization) — see
[`docs/architecture/roadmap.md`](../architecture/roadmap.md). This sprint
finally implements it, and immediately puts it to use: `ExecutionEngine`
and `AuthorizationEngine` publish lifecycle events through it.

This requires an ADR on the same three counts as ADR-0006/ADR-0007: it
introduces a new kernel subsystem, it defines a contract other subsystems
depend on, and it changes `ExecutionEngine`'s and `AuthorizationEngine`'s
behavior (optionally, additively).

## Decision

**A new top-level package, `src/mellivor_kernel/events/`,** implements the
"Event bus" responsibility as an **in-process** publish/subscribe
abstraction — explicitly not a distributed messaging system, not Kafka,
not NATS, not Redis:

- `Event` — an immutable base type (`event_id`, `occurred_at`) every
  concrete event derives from. Declared with `kw_only=True` fields so
  subclasses can add their own required fields without a dataclass
  field-ordering conflict.
- `EventHandler` — a `Protocol` (`handle(event) -> None`): anything capable
  of reacting to a published event.
- `EventBus` — a `Protocol` (`publish`, `subscribe`, `unsubscribe`): the
  contract every bus implementation satisfies. Publishers depend on this
  Protocol only, never on a concrete bus.
- `EventRegistration` — an opaque handle returned by `subscribe()`,
  required by `unsubscribe()`. Carries no reference to the handler itself.
- `InMemoryEventBus` — the only concrete implementation this sprint adds:
  synchronous, in-process, keyed by each event's *exact* type (no
  subscription to a base class receives subtype events — the simplest
  semantics that avoids ambiguity, not a limitation this sprint needed to
  resolve further). A handler's own exception is caught and logged, never
  propagated: one failing handler must never block delivery to the
  remaining handlers or break the publisher.
- `EventDispatchError` — raised only for misuse of the bus API itself
  (unsubscribing an inactive registration), never for a handler's own
  exception during `publish()`.

**`events` stays free of any knowledge of "execution," "authorization,"
"tools," or "providers."** The concrete event types this sprint's
integration needs —
`execution.events.{ExecutionStarted,ExecutionCompleted,ExecutionFailed}`
and
`authorization.events.{AuthorizationGranted,AuthorizationDenied}` — are
each owned by the subsystem that publishes them, not by `events` itself.
This keeps `events` reusable by any future subsystem (`workflow`, `agents`)
without modification, the same reasoning that keeps `tools`/`providers`
free of any `execution`-specific knowledge.

**`ExecutionEngine` and `AuthorizationEngine` each gain an optional
`event_bus: EventBus | None = None` constructor parameter.** With no bus
configured (the default), neither engine's behavior changes at all from
Sprint 8 — verified by the full Sprint 6–8 test suites passing unmodified.
When configured:

- `ExecutionEngine.execute()` publishes `ExecutionStarted` at the start,
  then exactly one of `ExecutionCompleted` or `ExecutionFailed` before
  returning — regardless of whether the failure came from an
  authorization denial or a dispatch failure, so a subscriber never needs
  to know which stage produced it (the failure's own detail remains in
  `error`/`stage`).
- `AuthorizationEngine.check()` — not `authorize()` — publishes
  `AuthorizationGranted` or `AuthorizationDenied`. `check()` is the
  adapter with access to the originating `ExecutionRequest.request_id`,
  which every published event carries for cross-subsystem correlation;
  `authorize()` remains a pure decision function with no request id to
  correlate against, so it never publishes.

**Publishing an event never requires knowledge of who (if anyone)
consumes it.** Neither engine imports `InMemoryEventBus`; both depend only
on `EventBus`. A future Kafka/NATS/Redis-backed `EventBus` implementation
is a drop-in replacement for `InMemoryEventBus` — no change to either
engine.

**No metrics, tracing, or audit logging were implemented.** Those remain
separate, unaddressed slices of the Observability/Security-primitives
responsibilities per ADR-0002; this sprint only publishes events; what (if
anything) subscribes to them and builds metrics/tracing/audit trail on top
is future work.

## Alternatives considered

- **Let event subscriptions match on base classes (e.g. subscribing to
  `Event` receives every event).** Rejected for this sprint: exact-type
  matching is simpler to reason about and implement correctly, and nothing
  in this sprint's integration needs hierarchical subscription. Revisit
  only if a real consumer needs it.
- **Have a failing handler's exception propagate out of `publish()`.**
  Rejected: a publisher (`ExecutionEngine`) must never be broken by a
  misbehaving subscriber it has no relationship with beyond "subscribed to
  this event type" — consistent with ADR-0004's "errors are translated at
  the boundary."
- **Define `ExecutionStarted`/`ExecutionCompleted`/etc. inside the
  `events` package itself.** Rejected: would force `events` to know about
  `execution`'s and `authorization`'s vocabulary, undermining its
  reusability for `workflow`/`agents` later — the sprint's design goals
  explicitly call for "provider-agnostic event infrastructure."
  Consistent with keeping `tools`'s built-in demonstration tools out of
  the generic `tools` contract too.
- **Publish events from `AuthorizationEngine.authorize()` instead of
  `check()`.** Rejected: `authorize()` takes only an `AuthorizationRequest`,
  which has no execution request id to correlate events against; `check()`
  is the integration point that has one, and is also the method
  `ExecutionEngine` actually calls.
- **Make `event_bus` a required constructor argument on either engine.**
  Rejected: a breaking change to an already-shipped public constructor,
  for the same reason ADR-0007 kept `authorizer` optional.

## Consequences

- `tools`, `providers`, `core` remain unaware of `events`; `execution` and
  `authorization` each depend on it directly (for `Event`/`EventBus`), a
  normal dependency on generic infrastructure — not the kind of coupling
  ADR-0007 inverted away from, since `events` (unlike `authorization`)
  contains no decision logic for `execution` to stay ignorant of.
- Any future subsystem wanting to publish or subscribe to kernel events
  depends only on `events.EventBus`/`events.Event`, and defines its own
  concrete event types the same way `execution`/`authorization` do here.
- `docs/architecture.md` records `events` as the third top-level package
  (alongside `bootstrap` and `execution`) placing a previously-unplaced
  ADR-0002 responsibility, and `docs/architecture/roadmap.md` records that
  Sprint 9 finally delivered it after three deferrals.
- Metrics, tracing, and audit logging remain explicitly out of scope and
  unpositioned; a future subsystem building them on top of `events` would
  itself need a design decision (and likely an ADR) about how it
  subscribes and what it does with what it receives.
