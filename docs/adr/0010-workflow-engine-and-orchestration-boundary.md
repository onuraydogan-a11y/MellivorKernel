# 0010. Workflow Engine, and the orchestration/execution boundary

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names
**Workflow engine** as a fixed kernel responsibility with a reserved
package (`workflow/`) since Sprint 1, but no implementation — the same
situation `events` and `memory` were in before Sprints 9 and 11
([ADR-0008](0008-event-bus-and-lifecycle-events.md),
[ADR-0009](0009-memory-subsystem-and-execution-recording.md)). This
sprint implements it: `WorkflowEngine` composes multiple
`ExecutionEngine.execute()` calls into a sequential run.

This requires an ADR on two counts: it introduces a new subsystem with
three new dependency edges at once (`workflow → execution`,
`workflow → memory`, `workflow → events`), and it fixes, as a permanent
constraint, the boundary between orchestration and execution --
`ExecutionEngine` remains the kernel's only execution entry point, and
`execution` (and everything below it) must never depend on `workflow`.

## Decision

**A new top-level package, `src/mellivor_kernel/workflow/`,** orchestrates
multiple execution steps -- it never executes a tool or provider itself:

- `WorkflowStep` — names a single step: an
  `execution.ExecutionRequest` to delegate to `ExecutionEngine`, the
  permissions claimed for it, and whether a failure on this step should
  stop the workflow (`continue_on_failure`, default `False`).
- `WorkflowDefinition` — an immutable, reusable "recipe": a `name`, an
  ordered `steps` tuple (may be empty), and free-form `metadata`. Rejects
  duplicate step names at construction -- they would silently collide as
  keys in `WorkflowResult.step_results`.
- `Workflow` — a single, identified *run* of a `WorkflowDefinition`
  (`workflow_id`, auto-generated), the same "definition vs. run" split
  `execution.ExecutionRequest`'s auto-generated `request_id` already
  establishes for a single execution.
- `WorkflowContext` — the context shared across a run's steps: the
  `ExecutionContext` passed to every step (identical throughout), and
  `step_results` -- the outcome of every step completed so far.
  `WorkflowEngine` threads a *new* `WorkflowContext` between steps
  (immutable replace, not mutation) with `step_results` extended each
  time; this is what "shared context" means.
- `WorkflowResult` — the outcome: `success`, `step_results`, and, on a
  stopped run, `error`/`stopped_at`. `success` tracks whether the run
  completed without being *stopped* early -- not whether every step
  individually succeeded; a step with `continue_on_failure=True` can fail
  without preventing overall success. Same invariant-validating
  `__post_init__` pattern as `ExecutionResult`/`AuthorizationResult`.
- `WorkflowEngine` — `run(workflow, context) -> WorkflowResult`: iterates
  `workflow.definition.steps` strictly in sequence, calling
  `self._execution_engine.execute(step.request, ..., granted_permissions=step.granted_permissions)`
  for each. A step's failure without `continue_on_failure` returns
  immediately -- no further step runs. Publishes `WorkflowStarted` once,
  then exactly one of `WorkflowCompleted`/`WorkflowFailed`, and records
  its own outcome to memory, all via constructor-injected
  `EventBus`/`MemoryStore` (optional, `None` by default -- no behavior
  change if unconfigured).
- `WorkflowError` — raised only for invalid data (a malformed
  `WorkflowStep`/`WorkflowDefinition`/`WorkflowResult`); a step failing
  during a run is a normal, non-raising outcome captured in
  `WorkflowResult`.

**`WorkflowEngine` receives `ExecutionEngine`, `MemoryStore`, and
`EventBus` entirely via constructor injection** -- it never constructs any
of the three itself, per this sprint's explicit instruction. This mirrors
`ExecutionEngine`'s own pattern for `Authorizer`/`EventBus`/`MemoryStore`:
optional, additive, dependency-injected, defaulting to "do nothing" when
unconfigured.

**Memory: written unconditionally when configured; read is a first-class,
tested capability of the same `MemoryStore`, not a separate mechanism.**
`WorkflowEngine` records a workflow-level summary (`workflow_id`, name,
success, step count) after every run. "Never bypass memory abstractions"
is satisfied by construction: there is no second, ad hoc memory path --
only `MemoryStore.add()`/`.get()`/`.search()`, the same contract
`execution` already uses. The integration test explicitly reads back what
`WorkflowEngine` wrote through the identical `MemoryStore` instance,
proving both directions work through the one abstraction.

**Own event types, not part of `events` itself.** `WorkflowStarted`,
`WorkflowCompleted`, `WorkflowFailed` live in `workflow/events.py`, owned
by `workflow` -- the same reasoning that keeps `execution.events` and
`authorization.events` out of the generic `events` package (ADR-0008): it
stays free of any knowledge of "workflow" as a concept, reusable by any
future subsystem unmodified.

**No parallel execution, no scheduling, no cron, no persistence beyond
whatever `memory` itself provides, and no dynamic step construction
(a step's `ExecutionRequest` is static, built before the run starts --
it cannot reference an earlier step's result to build itself).** All
explicitly out of scope for this sprint, per its instruction; the last
point is also why `WorkflowContext.step_results` matters more as a
*proven mechanism* for a future capability than as something a step
observably uses today -- see Alternatives below.

## Alternatives considered

- **Let `WorkflowStep`s call tools/providers directly, or reach into
  `Dispatcher`.** Rejected: the sprint's explicit premise is that
  `ExecutionEngine` remains the kernel's *only* execution entry point.
  `WorkflowEngine` composing calls to it, and nothing else, is what keeps
  orchestration and execution responsibilities separated -- the same
  separation `ADR-0006` established between `execution` and `tools`/
  `providers`.
- **Support dynamic step construction** (a step's request built from an
  earlier step's `ExecutionResult` at run time). Rejected for this
  sprint: real design work (a templating/expression mechanism) that
  should wait for a concrete consumer (most likely `agents`) to define
  the actual need, rather than guessing a shape here. `WorkflowContext`
  already threading accumulated `step_results` is deliberately the seam
  a future sprint would extend, not a placeholder invented without use.
- **Treat any individual step failure as an overall workflow failure**,
  regardless of `continue_on_failure`. Rejected: it would make
  `continue_on_failure` pointless -- the whole point of tolerating a
  step's failure is that the workflow still completes. `stopped_at`
  (set only when a failure actually halted the run) is the more useful
  signal for "did this workflow reach the end," with `step_results`
  available for "did every step individually succeed."
- **Make `execution_engine`/`memory`/`event_bus` required constructor
  arguments** rather than the latter two optional. Rejected for the
  latter two: the same reasoning ADR-0008/ADR-0009 already gave for
  `ExecutionEngine` -- optional-with-a-safe-default costs nothing and
  avoids forcing every caller to wire infrastructure it may not need yet.
  `execution_engine` itself is required: a `WorkflowEngine` with nothing
  to delegate to cannot do anything meaningful.

## Consequences

- `execution`, `authorization`, `memory`, `events`, `tools`, `providers`,
  and `bootstrap` are all byte-for-byte unchanged by this sprint --
  verified by the entire prior test suite passing unmodified. `workflow`
  is the only new dependency edge, and it points one way only.
- `execution` (and everything it depends on) must never import
  `workflow` -- this ADR fixes that direction as a permanent constraint,
  the same kind of guarantee ADR-0007 gave for `authorization`/
  `execution` and ADR-0009 gave for `memory`/providers.
- A future `agents` subsystem that wants to compose multi-step behavior
  is expected to depend on `workflow.WorkflowEngine` (or drive
  `execution.ExecutionEngine` directly for a single step), never
  reimplement sequencing of its own.
- Dynamic step construction, parallel steps, scheduling, and workflow
  persistence remain explicitly open, each requiring its own design
  decision (and likely its own ADR) once a concrete need is established.
