# `workflow` subsystem spec

Status: Implemented (Sprint 12); additive v1.1 evolution shipped in Sprint 30.

Public contract exported from `mellivor_kernel.workflow`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0010](../adr/0010-workflow-engine-and-orchestration-boundary.md) for
why this subsystem exists and the orchestration/execution boundary it
fixes permanently, and
[ADR-0025](../adr/0025-workflow-execution-options-compatibility-repair.md)
for the additive dynamic-request, opt-in parallel, and scheduling surface.

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

This is exactly the v1.0 public dataclass: field order, constructor defaults,
annotations, repr/equality/hash participation, and `asdict()` shape are
unchanged. Sprint 30 execution metadata is deliberately not stored here.

A step never executes anything itself. Every resolved `ExecutionRequest`
delegates to `ExecutionEngine.execute()`.
Permissions and `continue_on_failure` retain their v1.0 meanings unchanged.

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
`WorkflowResult.step_results`). All validation failures raise `WorkflowError`.

## `WorkflowExecutionOptions`

An additive immutable (`frozen=True, slots=True`) value applied to a single
run, without changing `WorkflowStep` or `WorkflowDefinition`:

```python
request_resolvers: Mapping[str, RequestResolver] = field(default_factory=dict)
parallel_groups: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
not_before: Mapping[str, datetime] = field(default_factory=dict)

RequestResolver = Callable[[WorkflowContext, ExecutionRequest], ExecutionRequest]
```

Keys are existing, unique step names. Unknown or blank names are rejected.
Parallel group members must be unique, contiguous, and in declared workflow
order. `not_before` values must be timezone-aware. The engine snapshots the
supplied mappings before execution, so later caller mutation cannot change an
in-progress run.

A resolver is called once with accumulated prior results and the step's
required original request. It returns the request to execute. There is no
expression language, string/code evaluation, retry, or speculative call.
Resolver exceptions and invalid return types become ordinary failed
`ExecutionResult` values with `metadata["stage"] == "dynamic_request"`.

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
after each step — this is what makes the context "shared." A configured
request resolver reads earlier results from this accumulated
snapshot. Siblings in a parallel group receive the identical pre-group
snapshot; the group is folded into a fresh context in declared order before
the next unit begins.

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
    max_concurrency: int | None = None,
    clock: Clock | None = None,
) -> None

def run(
    self,
    workflow: Workflow,
    context: WorkflowContext,
    *,
    options: WorkflowExecutionOptions | None = None,
) -> WorkflowResult
```

All infrastructure is received via dependency injection — `WorkflowEngine`
never constructs an `ExecutionEngine`, a memory backend, or an event bus
itself.

- Logs the start of the run and publishes `WorkflowStarted`.
- Iterates ordered execution units. Steps run inline exactly as in v1.0 unless
  named in an options `parallel_groups` entry. A configured contiguous group
  runs in a thread pool scoped to that group. `max_concurrency`, when set,
  bounds workers.
  For each resolved request, calls
  `execution_engine.execute(resolved_request, context.execution_context, granted_permissions=step.granted_permissions)`.
  `WorkflowEngine` never touches a tool or provider, `Dispatcher`, or
  authorization directly — everything about running one step (including
  whether it's authorized) is `ExecutionEngine`'s own responsibility,
  unchanged.
- Records the step's `ExecutionResult` in `step_results` and threads a
  new `WorkflowContext` with it included, for whatever execution unit runs
  next. Parallel results are presented in declared order, independent of
  completion order; siblings receive the same pre-group context.
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

### Dynamic, parallel, and failure semantics

Dependencies are expressed by sequence boundaries: a resolver reads only
completed earlier units, while siblings in a group are independent. The first
normal stopping failure in declared order determines `stopped_at`. Cancellation
of queued siblings is best-effort; already running work completes. One
unexpected execution exception propagates unchanged, matching v1.0; multiple
unexpected branch exceptions are raised in an `ExceptionGroup`, in declared
order.

Parallel execution assumes the injected execution stack is safe for concurrent
calls. A shared `SQLiteMemoryStore` connection retains SQLite's same-thread
default and must not be used across parallel branches. Use thread-safe
dependencies, isolate them per thread, or keep those workflows sequential.

### Scheduling semantics and limitations

`Clock` is the public time-source protocol; `SystemClock` returns aware UTC
time. When `clock.now()` is earlier than a step's options `not_before` value,
request construction and execution do not occur, and the step fails with
`metadata["stage"] == "scheduling"`.
At or after the timestamp it executes immediately. Tests can inject a fake
clock.

This is an eligibility primitive, not a scheduler service. Kernel does not
sleep, poll, retry, persist pending executions, start background threads,
provide cron, or wake itself after restart. An external runtime invokes
`run()` at the intended time.

### Backward compatibility guarantee

All v1.0 workflow types remain present and frozen. `WorkflowStep` and
`WorkflowDefinition` retain their exact v1.0 public dataclass shapes. Existing
constructors and two-argument `WorkflowEngine.run()` calls need no changes.
New engine arguments are keyword-only and optional; with `options=None`, static
workflows retain identical ordering, context, failure, event, memory, and
return-value behavior.

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
