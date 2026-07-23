# 0007. Authorization Engine, decoupled from Execution Core via a structural contract

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names
**Security primitives** as a fixed kernel responsibility with no package
placement decided, explicitly left open for "a future ADR." Separately,
Sprint 7's integration gate
([`docs/reviews/sprint7-execution-core-integration-gate.md`](../reviews/sprint7-execution-core-integration-gate.md))
documented a concrete gap: `Dispatcher` never had a way to forward granted
permissions to `ToolExecutionPipeline`, so no tool declaring required
permissions (e.g. `HealthCheckTool`) could ever succeed when driven through
`ExecutionEngine` -- only permission-free tools could.

This sprint places a slice of "Security primitives" -- deciding whether an
execution request is authorized -- as its own subsystem, `authorization`,
and closes the Sprint 7 gap by wiring it into `ExecutionEngine`. This
requires an ADR on three counts, per `docs/adr/README.md`: it introduces a
new kernel subsystem, it defines a contract other subsystems will depend
on, and it changes `ExecutionEngine`'s behavior in a way ADR-0006 explicitly
described as future work ("Authorization... ExecutionEngine performs no
permission/authorization checks of its own").

## Decision

**A new top-level package, `src/mellivor_kernel/authorization/`,** decides
only whether an `ExecutionRequest` is authorized. It never executes, never
dispatches, and never contains business logic:

- `AuthorizationRequest` -- an immutable request to authorize a
  `target`/`operation`, with the caller's claimed `granted_permissions`
  (a `PermissionSet`). Independent of `ExecutionRequest`: testable without
  an `ExecutionContext` or a running kernel.
- `PermissionSet` -- a thin, immutable wrapper around the *existing*
  `tools.permissions.Permission` model. No new permission vocabulary is
  introduced, per this sprint's explicit instruction.
- `PermissionResolver` -- resolves the permissions *required* for a
  `target`/`operation`, by reading a tool's already-declared
  `BaseTool.permissions` from a `ToolRegistry`. For
  `ExecutionTarget.PROVIDER`, the current `BaseProvider` contract declares
  no permissions at all, so the resolver always returns an empty
  requirement for provider targets -- honest reflection of what the
  contract states, not a gap. For an unregistered tool, the resolver also
  returns empty: reporting "no such tool" is `Dispatcher`'s job (already
  implemented, unchanged), not something `PermissionResolver` duplicates.
- `AuthorizationResult` -- the immutable outcome: `granted`, `reason`
  (required on denial), and `granted_permissions` (the claim found
  sufficient, on success).
- `AuthorizationEngine` -- compares required vs. claimed permissions using
  the *existing* `tools.permissions.missing_permissions()` function (no new
  diffing logic invented), via two methods:
  - `authorize(AuthorizationRequest) -> AuthorizationResult` -- the pure
    decision, requiring only `authorization`'s own types.
  - `check(ExecutionRequest, ExecutionContext, *, granted_permissions) -> AuthorizationResult` --
    the adapter `ExecutionEngine` actually calls.
- `AuthorizationError` -- raised only for invalid data (a malformed
  `AuthorizationRequest`/`AuthorizationResult`); a denial is a normal,
  non-raising `AuthorizationResult(granted=False, ...)`.

**Execution never imports `authorization` -- the dependency runs the other
way.** `execution.contracts` (new) defines two small structural Protocols:
`AuthorizationOutcome` (`granted`, `reason`) and `Authorizer`
(`check(request, context, *, granted_permissions) -> AuthorizationOutcome`).
`ExecutionEngine` depends only on these Protocols; `AuthorizationEngine`
satisfies `Authorizer` structurally without `execution` ever importing
`authorization`. This is the exact inversion `core.contracts.KernelSettings`
already established for `core`/`config` in Sprint 2 -- reused here rather
than inventing a new decoupling mechanism.

**`ExecutionEngine.__init__` gains an optional `authorizer: Authorizer | None = None`.**
`execute()` gains an optional `granted_permissions: frozenset[str] = frozenset()`
keyword parameter -- mirroring `ToolExecutionPipeline.run`'s existing
convention of passing permissions per call rather than embedding them in
the request object. Neither `ExecutionRequest`, `ExecutionContext`, nor
`ExecutionResult` changed. When an `authorizer` is configured and denies, a
failed `ExecutionResult` (`metadata["stage"] == "authorization"`) is
returned *before* `Dispatcher` is ever reached, per the flow this sprint
implements: `ExecutionRequest -> Authorization -> Dispatcher ->
Tool/Provider -> ExecutionResult`. With no `authorizer` configured,
behavior is byte-for-byte identical to before this sprint -- zero
regression for existing callers.

**`Dispatcher.dispatch()` gains the matching `granted_permissions: frozenset[str] = frozenset()`.**
This is what actually closes the Sprint 7 gap: on the tool path, raw
permission strings are converted to `Permission` values and forwarded into
`ToolExecutionPipeline.run(..., granted_permissions=...)`. An invalid
permission string is translated into a failed `ExecutionResult`
(`metadata["stage"] == "permission_check"`) rather than raised, consistent
with ADR-0004. The provider path ignores the parameter -- `BaseProvider`
has nothing to check it against.

## Alternatives considered

- **Put `AuthorizationResult`/`Authorizer` directly inside `execution`.**
  Rejected: the sprint's scope explicitly lists these as `authorization`
  subsystem deliverables, and folding the concrete decision type into
  `execution` would blur "execution must never know HOW permissions are
  resolved" into "execution defines how permissions are resolved."
- **Have `execution` depend directly on `authorization`.** Rejected: this
  is exactly the dependency the design rules for this sprint forbid, and
  it would make every future consumer of authorization (`workflow`,
  `agents`) require a concrete `authorization` import instead of the small
  Protocol seam.
- **Embed `granted_permissions` in `ExecutionRequest`.** Rejected:
  `ToolExecutionPipeline.run` already established permissions as a
  per-call argument, not request data; keeping `ExecutionRequest` textually
  unchanged also minimizes risk to an already-shipped, ADR-0006-governed
  contract.
- **Make `authorizer` a required `ExecutionEngine` constructor argument.**
  Rejected: a breaking change to an already-shipped public constructor.
  Optional-with-a-safe-default (no authorizer = no permissions ever
  granted, same as before) preserves compatibility while still making
  authorization the supported way to close the gap once wired in.
- **Have `PermissionResolver` raise for an unregistered tool.** Rejected:
  would duplicate `Dispatcher`'s existing "not registered" handling in a
  second place, and risks the two diverging. Returning an empty
  requirement is safe because an unregistered tool still cannot execute --
  `Dispatcher`'s own lookup fails it regardless of what authorization
  decided.

## Consequences

- `ExecutionEngine(dispatcher)` (no authorizer) and
  `Dispatcher.dispatch(request, context)` (no permissions) continue to
  work exactly as before this sprint -- verified by the unchanged Sprint
  6/7 test suites passing unmodified.
- Any permissioned tool now succeeds through `ExecutionEngine` when (and
  only when) an `AuthorizationEngine` is wired in and the caller supplies
  sufficient `granted_permissions` -- see
  `tests/test_authorization_integration.py` and
  `examples/execution_with_authorization.py`, both driving
  `HealthCheckTool` (`kernel.internal`) end-to-end.
- Provider targets are authorized trivially today because `BaseProvider`
  declares no permissions. If a future ADR adds a permission model to
  `BaseProvider`, `PermissionResolver.resolve_required_permissions` is the
  one place that needs to change.
- `docs/architecture.md` records `authorization` as (partially) placing
  ADR-0002's "Security primitives" responsibility; the rest of Security
  primitives (secrets, encryption, etc.) remain unplaced.
- ADR-0006's statement that "ExecutionEngine performs no permission/
  authorization checks of its own" is superseded by this ADR; ADR-0006's
  other decisions (Dispatcher's two targets, the request/context/result
  contracts) are unaffected and remain in force.
