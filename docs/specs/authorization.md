# `authorization` subsystem spec

Status: Implemented (Sprint 8; events in Sprint 9).

Public contract exported from `mellivor_kernel.authorization`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
for why this subsystem exists, why it depends on `execution` rather than
the other way around, and what it deliberately excludes (execution,
dispatch, business policy); see
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md) for its
published events.

## Exceptions

`authorization/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `AuthorizationError` — the only exception this subsystem raises, and
  only for invalid data: a malformed `AuthorizationRequest` or
  `AuthorizationResult`. A denial is never an exception — it is a normal
  `AuthorizationResult(granted=False, reason=...)`.

## `PermissionSet`

An immutable (`frozen=True, slots=True`) wrapper around
`frozenset[Permission]` — reuses `tools.permissions.Permission` as-is; no
new permission vocabulary. `PermissionSet.empty()` returns an empty set.

## `AuthorizationRequest`

An immutable (`frozen=True, slots=True`) dataclass — the input to
`AuthorizationEngine.authorize()`:

```python
target: ExecutionTarget
operation: str
granted_permissions: PermissionSet = field(default_factory=PermissionSet.empty)
```

Deliberately independent of `execution.ExecutionRequest` beyond sharing the
same `target`/`operation` vocabulary — testable without an
`ExecutionContext` or a running kernel. `__post_init__` rejects a blank
`operation`, raising `AuthorizationError`.

## `AuthorizationResult`

An immutable (`frozen=True, slots=True`) dataclass — the outcome:

```python
granted: bool
granted_permissions: PermissionSet = field(default_factory=PermissionSet.empty)
reason: str | None = None
```

`__post_init__` enforces: a denial (`granted=False`) requires a non-empty
`reason` and forbids `granted_permissions`; a grant (`granted=True`)
forbids `reason`. Violating any of these raises `AuthorizationError`.

Structurally satisfies `execution.contracts.AuthorizationOutcome`
(`granted`, `reason`) — `execution` never imports this class by name.

## `PermissionResolver`

```python
def __init__(self, tool_registry: ToolRegistry) -> None

def resolve_required_permissions(self, target: ExecutionTarget, operation: str) -> PermissionSet
```

- `ExecutionTarget.TOOL` — returns the looked-up tool's declared
  `BaseTool.permissions`. The *only* thing this subsystem reads from the
  Tool Runtime; it never registers, unregisters, or executes a tool.
- `ExecutionTarget.PROVIDER` — always `PermissionSet.empty()`.
  `BaseProvider` has no permission model in its current contract, so there
  is nothing to require — not a gap, an honest reflection of what the
  contract states.
- An unregistered tool id — also `PermissionSet.empty()`, deliberately.
  Reporting "no such tool" is `Dispatcher`'s job (already implemented); an
  authorization decision that always "passes" for an unknown operation is
  safe because that operation still cannot execute — `Dispatcher`'s own
  registry lookup fails it regardless of what authorization decided.

## `authorization.events`

Two of `authorization`'s own event types (`events.Event` subclasses),
published only by `AuthorizationEngine.check()` (never by `authorize()`
— see below):

- `AuthorizationGranted` (`request_id`, `target`, `operation`,
  `granted_permissions: frozenset[str]`).
- `AuthorizationDenied` (`request_id`, `target`, `operation`, `reason`).

`request_id` is the originating `ExecutionRequest.request_id`, letting a
subscriber correlate an authorization event with the `execution.events`
sequence for the same request. See ADR-0008 and `docs/specs/events.md`.

## `AuthorizationEngine`

```python
def __init__(
    self, permission_resolver: PermissionResolver, *, event_bus: EventBus | None = None
) -> None

def authorize(self, request: AuthorizationRequest) -> AuthorizationResult

def check(
    self,
    request: ExecutionRequest,
    context: ExecutionContext,
    *,
    granted_permissions: frozenset[str],
) -> AuthorizationResult
```

- `authorize()` — the pure decision. Resolves required permissions via
  `PermissionResolver`, compares against `request.granted_permissions`
  using the *existing*
  `tools.permissions.missing_permissions(required, granted)` — no new
  diffing logic. Grants if nothing is missing; otherwise denies, naming
  every missing permission in `reason`. **Never publishes events** — it
  takes only an `AuthorizationRequest`, which has no execution request id
  to correlate an event against.
- `check()` — the adapter `execution.ExecutionEngine` actually calls, and
  the only method in this subsystem that touches `execution` types or
  publishes events. Converts each raw permission string in
  `granted_permissions` into a `tools.permissions.Permission`; an invalid
  format (a `ToolValidationError`) is translated into a denied
  `AuthorizationResult` (and a published `AuthorizationDenied`) rather
  than raised, consistent with ADR-0004. Builds an `AuthorizationRequest`
  from `request.target`/`request.operation`/the validated claim, delegates
  to `authorize()`, then publishes `AuthorizationGranted` or
  `AuthorizationDenied` when `event_bus` is configured. With
  `event_bus=None` (the default), no events are ever published —
  identical to this engine's behavior before Sprint 9.

`check()`'s signature satisfies `execution.contracts.Authorizer`
structurally — `execution` never imports `AuthorizationEngine` by name; see
`docs/specs/execution.md`.

## Dependency relationship

```
authorization → execution, tools, events, core
```

`authorization` depends on `execution` (`ExecutionRequest`,
`ExecutionContext`, `ExecutionTarget`), `tools` (`Permission`,
`missing_permissions`, `ToolRegistry`, `ToolRegistrationError`,
`ToolValidationError`), and `events` (`Event`, `EventBus`) — never on
`providers`. `execution` has **no** dependency on `authorization`; it
depends only on the `Authorizer`/`AuthorizationOutcome` Protocols it
defines itself (see `execution.contracts`). `tools` and `events` have no
dependency on `authorization`.
