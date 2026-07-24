# `authorization` subsystem spec

Status: Implemented (Sprint 8; events in Sprint 9; audit recording in
Sprint 17).

Public contract exported from `mellivor_kernel.authorization`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md)
for why this subsystem exists, why it depends on `execution` rather than
the other way around, and what it deliberately excludes (execution,
dispatch, business policy);
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md) for its
published events; and
[ADR-0012](../adr/0012-security-foundation.md) for the security foundation
it optionally records grant/deny decisions to.

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
    self,
    permission_resolver: PermissionResolver,
    *,
    event_bus: EventBus | None = None,
    audit_sink: AuditSink | None = None,
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
  every missing permission in `reason`. **Never publishes events or
  records audit entries** — it takes only an `AuthorizationRequest`, which
  has no execution request id to correlate either against.
- `check()` — the adapter `execution.ExecutionEngine` actually calls, and
  the only method in this subsystem that touches `execution` types,
  publishes events, or records audit entries. Converts each raw permission
  string in `granted_permissions` into a `tools.permissions.Permission`;
  an invalid format (a `ToolValidationError`) is translated into a denied
  `AuthorizationResult` (and a published `AuthorizationDenied`) rather
  than raised, consistent with ADR-0004. Builds an `AuthorizationRequest`
  from `request.target`/`request.operation`/the validated claim, delegates
  to `authorize()`, then publishes `AuthorizationGranted` or
  `AuthorizationDenied` when `event_bus` is configured, and records the
  same decision as a `security.AuditRecord` when `audit_sink` is
  configured — for every outcome, including the malformed-permission
  denial path. `AuditRecord.subject` is `request.request_id` (the same
  correlation key the events use) and `AuditRecord.action` is
  `"<target>:<operation>"`, so a recorded entry names both what was
  evaluated and which request it belongs to without any change to
  `AuditRecord`'s own shape. With `event_bus=None` or `audit_sink=None`
  (both default), the corresponding mechanism is skipped — identical to
  this engine's behavior before Sprint 9 (events) or Sprint 17 (audit).
  The two mechanisms are independent: configuring one never affects the
  other.

`check()`'s signature satisfies `execution.contracts.Authorizer`
structurally — `execution` never imports `AuthorizationEngine` by name; see
`docs/specs/execution.md`.

## Dependency relationship

```
authorization → execution, tools, events, security, core
```

`authorization` depends on `execution` (`ExecutionRequest`,
`ExecutionContext`, `ExecutionTarget`), `tools` (`Permission`,
`missing_permissions`, `ToolRegistry`, `ToolRegistrationError`,
`ToolValidationError`), `events` (`Event`, `EventBus`), and, as of
Sprint 17, `security` (`AuditRecord`, `AuditSink`, `SecurityDecision`) —
consumed only through the abstract `AuditSink` Protocol, never a concrete
sink; `security` itself depends only on `core`, so this adds no new
transitive dependency beyond that. `authorization` never depends on
`providers`. `execution` has **no** dependency on `authorization`; it
depends only on the `Authorizer`/`AuthorizationOutcome` Protocols it
defines itself (see `execution.contracts`). `tools`, `events`, and
`security` have no dependency on `authorization`.
