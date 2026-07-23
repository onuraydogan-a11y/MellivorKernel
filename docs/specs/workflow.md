# `workflow` subsystem spec

Status: Implemented (Sprint 12).

Public contract exported from `mellivor_kernel.workflow`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0010](../adr/0010-workflow-engine-and-orchestration-boundary.md) for
why this subsystem exists and the orchestration/execution boundary it
fixes permanently.

## Exceptions

`workflow/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `WorkflowError` — the only exception this subsystem raises, and only
  for invalid data (a malformed `WorkflowStep`, `WorkflowDefinition`, or
  `WorkflowResult`). A step failing during a run is never an exception —
  it is a normal outcome captured in `WorkflowResult`.

## `WorkflowStep`

An immutable (`frozen=True, slots=True`) dataclass — one step:

```python
name: str
request: ExecutionRequest
granted_permissions: frozenset[str] = field(default_factory=frozenset)
continue_on_failure: bool = False
```

A step never executes anything itself — `request` is the
`execution.ExecutionRequest` `WorkflowEngine` delegates to
`ExecutionEngine.execute()`, unchanged. `granted_permissions` is forwarded
unchanged too. `__post_init__` rejects a blank `name`, raising
`WorkflowError`.

## `WorkflowDefinition`

An immutable (`frozen=True, slots=True`) dataclass — the reusable
"recipe":

```python
name: str
steps: tuple[WorkflowStep, ...] = field(default_factory=tuple)
metadata: Mapping[str, object] = field(default_factory=dict)
```

`steps` may be empty. `__post_init__` rejects a blank `name` and rejects
duplicate step names (they would silently collide as keys in
`WorkflowResult.step_results`), both raising `WorkflowError`.

## `Workflow`

An immutable (`frozen=True, slots=True`) dataclass — a single, identified
run of a `WorkflowDefinition`:

```python
definition: WorkflowDefinition
workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

`workflow_id` is auto-generated (a UUID4 string) if not supplied, the same
convention `execution.ExecutionRequest.request_id` uses, for log/event/
memory correlation.

## `WorkflowContext`

An immutable (`frozen=True, slots=True`) dataclass — the context shared
across a run's steps:

```python
execution_context: ExecutionContext
step_results: Mapping[str, ExecutionResult] = field(default_factory=dict)
```

`execution_context` is passed to `ExecutionEngine.execute()` for every
step, identical throughout the run. `step_results` holds every step's
outcome completed so far; `WorkflowEngine` threads a *new*
`WorkflowContext` (immutable replace, never mutation) with this extended
after each step — this is what makes the context "shared." A step's own
`request` is static in this sprint (built before the run starts), so
nothing yet reads an earlier step's result to build a later one — the
mechanism exists and is tested; using it for dynamic step construction is
future work.

## `WorkflowResult`

An immutable (`frozen=True, slots=True`) dataclass — the outcome of one
`WorkflowEngine.run()` call:

```python
success: bool
step_results: Mapping[str, ExecutionResult] = field(default_factory=dict)
error: str | None = None
stopped_at: str | None = None
```

`success` tracks whether the run completed **without being stopped
early** — not whether every individual step succeeded. A step with
`continue_on_failure=True` can fail without preventing overall success;
callers wanting to know whether *any* step failed should inspect
`step_results` directly. `__post_init__` enforces: `success=False`
requires a non-empty `error`; `success=True` forbids both `error` and
`stopped_at`. Violating any of these raises `WorkflowError`.

## `workflow.events`

Three of `workflow`'s own event types (`events.Event` subclasses),
published by `WorkflowEngine`, not part of the generic `events` package —
the same reasoning `execution.events`/`authorization.events` already
follow (ADR-0008):

- `WorkflowStarted` (`workflow_id`, `name`) — published once, at the
  start of `run()`.
- `WorkflowCompleted` (adds `step_count`) — published when the run
  completes without being stopped early.
- `WorkflowFailed` (adds `error`, `stopped_at: str | None = None`) —
  published when a step stops the run.

Exactly one of `WorkflowCompleted`/`WorkflowFailed` is published per
`run()` call, always preceded by `WorkflowStarted`.

## `WorkflowEngine`

The orchestration entry point.

```python
def __init__(
    self,
    execution_engine: ExecutionEngine,
    *,
    memory: MemoryStore | None = None,
    event_bus: EventBus | None = None,
) -> None

def run(self, workflow: Workflow, context: WorkflowContext) -> WorkflowResult
```

All infrastructure is received via dependency injection — `WorkflowEngine`
never constructs an `ExecutionEngine`, a memory backend, or an event bus
itself.

- Logs the start of the run and publishes `WorkflowStarted`.
- Iterates `workflow.definition.steps` **strictly in sequence** — no
  parallel execution. For each step, calls
  `execution_engine.execute(step.request, context.execution_context, granted_permissions=step.granted_permissions)`.
  `WorkflowEngine` never touches a tool or provider, `Dispatcher`, or
  authorization directly — everything about running one step (including
  whether it's authorized) is `ExecutionEngine`'s own responsibility,
  unchanged.
- Records the step's `ExecutionResult` in `step_results` and threads a
  new `WorkflowContext` with it included, for whatever step runs next.
- If the step failed and `continue_on_failure` is `False` (the default),
  stops immediately: publishes `WorkflowFailed`, records to memory (if
  configured), and returns a failed `WorkflowResult` naming the step in
  `error`/`stopped_at`. No further step runs.
- If every step ran without a stopping failure (including the empty-steps
  case, which is trivially successful), publishes `WorkflowCompleted`,
  records to memory (if configured), and returns a successful
  `WorkflowResult`.
- A `memory.add()` failure is caught and logged, never propagated — a
  misbehaving `MemoryStore` must never break a workflow run, the same
  guarantee `ExecutionEngine` already gives (ADR-0009).

With `event_bus=None`/`memory=None` (both default), no events are
published and nothing is recorded — identical to a `WorkflowEngine`
constructed with only `execution_engine`.

## Dependency relationship

```
workflow → execution, memory, events
```

`workflow` depends on `execution` (`ExecutionEngine`, `ExecutionContext`,
`ExecutionRequest`, `ExecutionResult`), `memory` (`MemoryEntry`,
`MemoryStore`), and `events` (`Event`, `EventBus`) — normal dependencies on
generic infrastructure and on the kernel's single execution entry point,
not the kind of coupling ADR-0007 inverted away from (none of the three
contain decision logic `workflow` needs to stay ignorant of).
`execution`, `authorization`, `memory`, `events`, `tools`, and `providers`
have **no** dependency on `workflow`, and never will — see ADR-0010.
