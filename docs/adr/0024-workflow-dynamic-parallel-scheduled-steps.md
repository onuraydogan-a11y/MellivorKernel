# 0024. Workflow evolution: dynamic steps, parallel execution, scheduling

Status: Superseded by [ADR-0025](0025-workflow-execution-options-compatibility-repair.md)
Date: 2026-08-26

> **Compatibility correction:** The Sprint 31 release audit rejected this
> ADR's direct additions to the frozen `WorkflowStep` dataclass as breaking
> under ADR-0005. ADR-0025 restores the v1.0 surface and relocates dynamic,
> parallel, and scheduling configuration to additive execution options. This
> document remains the historical record of the original Sprint 30 decision.

## Context

[ADR-0010](0010-workflow-engine-and-orchestration-boundary.md) shipped
`WorkflowEngine` with three named exclusions: "no parallel execution, no
scheduling, no cron, no persistence beyond whatever `memory` itself
provides, and no dynamic step construction (a step's `ExecutionRequest`
is static, built before the run starts)." Its own "Alternatives
considered" explicitly deferred dynamic steps as "real design work...
that should wait for a concrete consumer to define the actual need,
rather than guessing a shape here," and its "Consequences" named
"dynamic step construction, parallel steps, scheduling, and workflow
persistence" as each requiring its own future design decision.

Both [ADR-0019](0019-release-readiness-and-scope-lock.md) and
[ADR-0020](0020-release-decision-v1.0.md) classify exactly these three
("dynamic steps... parallel execution, and scheduling") as `Deferred to
v1.1`, judged "well-understood, boundable extensions... their shape is
already reasonably clear from ADR-0010's own deferral language."

This is Sprint 30, per direct Product-Owner instruction: implement all
three, additively, preserving v1.0.0 workflow behavior and API exactly.
Per the sprint's own framing, this is "the highest-risk v1.1 feature
sprint because it evolves an already-public workflow API surface" --
this ADR treats that risk with the corresponding weight.

### Architecture review

Before any design decision below, the following was inspected in full:
every file in `src/mellivor_kernel/workflow/` (`step.py`, `definition.py`,
`workflow.py`, `context.py`, `result.py`, `engine.py`, `events.py`,
`exceptions.py`, `__init__.py`), every file in `tests/workflow/`,
ADR-0010, the workflow responsibility row of ADR-0019 (quoted above),
`docs/specs/workflow.md`, `src/mellivor_kernel/execution/` in full
(`request.py`, `context.py`, `result.py`, `engine.py`, `contracts.py`,
`dispatch.py`), and `src/mellivor_kernel/tools/pipeline.py`. Findings
that directly shape this ADR:

1. **Every public workflow type is a frozen, `slots=True` dataclass**
   (`WorkflowStep`, `WorkflowDefinition`, `Workflow`, `WorkflowContext`,
   `WorkflowResult`) validated at construction via `__post_init__`,
   raising `WorkflowError` for invalid data only. None is a `Protocol` or
   plain mapping. `WorkflowEngine` is a concrete class, not an ABC/Protocol.
2. **Every constructor call site in this repository (`src/`, `tests/`,
   `examples/`) uses keyword arguments** for these five types -- confirmed
   by a full-repository grep; no positional construction exists anywhere.
   This matters directly: it means inserting or widening a field's default
   cannot silently break a call site's argument binding.
3. **`WorkflowEngine.run()` threads a *new* `WorkflowContext` between
   steps** (`dataclasses.replace(running_context, step_results=dict(...))`)
   -- never mutates the one it was given, and never mutates a completed
   step's `ExecutionResult` (itself frozen). The original caller-supplied
   `WorkflowContext` is provably untouched after `run()` returns (already
   directly tested,
   `test_shared_context_accumulates_step_results_as_the_workflow_progresses`).
4. **`ExecutionEngine.execute()` is 100% synchronous** -- no `async def`,
   no `asyncio`, no `threading`, no `concurrent.futures` usage anywhere in
   `src/` (confirmed by a full-source grep returning zero matches). The
   kernel has no existing async/sync boundary to preserve or violate --
   there is only "sync."
5. **A tool or provider's own exception never reaches `WorkflowEngine`**:
   `ToolExecutionPipeline.run()` catches `Exception` from `tool.execute()`
   and returns a failed `ToolResult`;
   `Dispatcher._dispatch_to_provider()` catches `Exception` from
   `provider.invoke()` and returns a failed `ExecutionResult`. In
   practice, `ExecutionEngine.execute()` returning without raising is the
   overwhelmingly common case; **there is still no `try`/`except` around
   `execution_engine.execute(...)` inside `WorkflowEngine.run()` itself**
   -- if `execute()` *did* raise (an `Authorizer`, `Dispatcher`, or
   `ExecutionEngine` bug, not a tool/provider failure), that exception
   propagates out of `run()` uncaught today, with no `WorkflowResult`
   returned and no `WorkflowFailed` published. This existing behavior is
   preserved exactly by every design below.
6. **`ExecutionEngine` itself holds no mutable state after `__init__`**
   (`_dispatcher`/`_authorizer`/`_event_bus`/`_memory`/`_observability` are
   all set once, never reassigned) -- calling `.execute()` concurrently
   from multiple threads on the same `ExecutionEngine` instance mutates
   nothing on that instance itself. Whether this is *safe overall*
   depends entirely on whether its own injected dependencies are safe for
   concurrent multi-threaded use -- see "Thread/async safety assumptions"
   under Part B below; this is a real, new consideration Sprint 30
   introduces, not a pre-existing guarantee.
7. **`WorkflowResult`/`WorkflowStarted`/`WorkflowCompleted`/`WorkflowFailed`
   are unchanged by every design below** -- no new field is added to any
   of them. `stopped_at`/`error` continue to name exactly one step.

**Conclusion: all three capabilities can be introduced additively**, with
zero change to any existing field's meaning, zero required-constructor
break, and zero change to observable behavior for a workflow that uses
none of the new fields. No architecture stop condition applies. This ADR
proceeds to design.

## Decision

### A. Dynamic steps

**`WorkflowStep` gains two new fields**, both optional, appended after
the existing four:

```python
name: str
request: ExecutionRequest | None = None  # was: ExecutionRequest (required)
granted_permissions: frozenset[str] = field(default_factory=frozenset)
continue_on_failure: bool = False
request_factory: Callable[[WorkflowContext], ExecutionRequest] | None = None  # new
parallel_group: str | None = None  # new -- see Part B
not_before: datetime | None = None  # new -- see Part C
```

**`request`'s type widens from `ExecutionRequest` to `ExecutionRequest |
None`, defaulting to `None`.** This is the one change to an existing
field, and it is deliberate, not incidental -- justified explicitly here
because it is the kind of change this sprint's own "architecture stop
conditions" warn against if done carelessly:

- It does **not** break any existing constructor call: every call site in
  this repository (finding 2 above) passes `request=<a real
  ExecutionRequest>` by keyword; none relies on `request` being
  positionally required or omittable-with-a-different-default.
- It does **not** change `request`'s meaning when set: a set `request` is
  still, exactly as before, the static `ExecutionRequest` delegated
  unchanged to `ExecutionEngine.execute()`.
- The alternative -- leaving `request` required and forcing a fully
  dynamic step's author to construct a throwaway, unused
  `ExecutionRequest` just to satisfy the type -- was rejected as a worse
  API for exactly the callers this feature exists to serve; see
  "Alternatives considered."

**`__post_init__` gains one new invariant**: exactly one of `request`/
`request_factory` must be set --

```python
if (self.request is None) == (self.request_factory is None):
    raise WorkflowError(
        "WorkflowStep must set exactly one of `request` (static) or `request_factory` (dynamic)."
    )
```

This is the entire "resolver abstraction" this sprint calls for -- **no
template language, no expression DSL, no string-based reference syntax**.
`request_factory` is a plain Python callable, `(WorkflowContext) ->
ExecutionRequest`, that the workflow's author writes directly (a
function, a lambda, or a small class with `__call__`). It reads whatever
it needs from `context.step_results: Mapping[str, ExecutionResult]` --
already a public, tested field since Sprint 12 -- using ordinary Python
(`context.step_results["earlier_step"].payload["field"]`). This satisfies
"no arbitrary code evaluation" definitionally: the kernel never
`eval()`s, `exec()`s, or interprets a string against workflow state; it
only *calls a function the caller supplied*, the same trust boundary
every dependency-injection seam in this kernel already has (an
`Authorizer`, an `EventBus`, a `MemoryStore` are all caller-supplied
callables/objects the kernel invokes without inspecting).

**Deterministic resolution semantics**: `request_factory` is called
exactly once per step execution, synchronously, in the same thread that
is running that step (see Part B for what "which thread" means for a
parallel step). The kernel does not retry it, cache its result, or call
it speculatively. Determinism of the factory's *own* logic (e.g., not
reading wall-clock time or randomness internally) is the caller's
responsibility, precisely as it already is for any Python callable a
consumer supplies to this kernel.

**Explicit missing-reference behavior**: if `request_factory(context)`
raises *any* exception (a `KeyError` for a step name not yet in
`step_results`, an `AttributeError`, anything), `WorkflowEngine` catches
it and synthesizes a failed `ExecutionResult`:

```python
ExecutionResult(
    success=False,
    error=f"Dynamic request construction failed for step {step.name!r}: {exc}",
    metadata={"stage": "dynamic_request"},
)
```

**Explicit type/value behavior**: if `request_factory(context)` returns
successfully but the value is not an `ExecutionRequest` instance, the
same failure shape is produced instead (`"...returned <type>, expected
ExecutionRequest."`). Neither case ever reaches
`ExecutionEngine.execute()` with a malformed value.

**This synthetic failed `ExecutionResult` then flows through the exact
same machinery every other step failure already uses** --
`step_results[step.name] = result`, the `continue_on_failure` check,
`WorkflowFailed`/`stopped_at` on a stop, memory recording. **No new
`WorkflowResult`/`WorkflowFailed` field, no new exception type, was
needed for this.** A "dynamic request construction failed" outcome is,
from every existing consumer's point of view, indistinguishable in shape
from "the tool/provider itself failed" -- distinguishable only via
`ExecutionResult.metadata["stage"]`, the same mechanism `Dispatcher`/
`ToolExecutionPipeline` already use for their own stage labels
(`"validate"`, `"permission_check"`, `"execute"`).

**No mutation of previous results**: `WorkflowContext.step_results` was
already, since Sprint 12, threaded as a fresh `dict` copy at each step
boundary (finding 3), and `ExecutionResult` was already frozen. Nothing
in this design changes either guarantee -- a `request_factory` reading
`context.step_results` reads a snapshot that cannot be retroactively
altered by anything that runs after it, and cannot itself corrupt a
prior snapshot even if it mutated the `dict` object it was handed (each
snapshot is now a distinct object; see Part B for why a factory never
receives a snapshot that includes a *still-running* sibling's result in
the first place).

**Existing static requests remain unchanged**: a `WorkflowStep` built the
old way (`request=<ExecutionRequest>`, `request_factory` omitted)
resolves to using `step.request` directly -- byte-for-byte the same value
`ExecutionEngine.execute()` receives today. Proven by re-running the
entire pre-existing `tests/workflow/test_engine.py` suite unmodified.

### B. Parallel execution

**`WorkflowStep.parallel_group: str | None = None`** is the entire
representation of "this step may run in parallel with its neighbors."
Steps are partitioned into **execution units**: a maximal run of
*consecutive* steps sharing the same non-`None` `parallel_group` value is
one unit, executed concurrently; any step with `parallel_group=None`
(the default -- every existing workflow) is its own unit of exactly one,
executed **inline, in the calling thread, with no `ThreadPoolExecutor`
involved at all** -- not merely "a pool of size one." This is deliberate:
per this sprint's own instruction, "do not add concurrency solely for
performance if the workflow graph does not explicitly request it," so a
workflow that never sets `parallel_group` never touches a thread pool,
anywhere, and its performance/behavior profile is identical to
pre-Sprint-30 `WorkflowEngine`.

**Dependency semantics: grouping, not a dependency graph.** This sprint
deliberately does **not** build a DAG resolver, a topological sort, or
per-step declared dependency edges -- that is materially closer to
"distributed orchestration," explicitly out of scope. The model is: units
execute strictly in the order they appear in `definition.steps`
(preserving the one true ordering source, exactly as today); within one
unit, every step is assumed independent of every other step *in that same
unit* -- the caller expresses "these are safe to run together" purely by
placing them adjacently under the same `parallel_group` name, and
expresses "this must wait for the group before it" by placing it after
the group in `steps`. This is the entire dependency vocabulary this
sprint provides, matching "prefer a small... mechanism... over a new
DSL" applied to dependencies too, not only request construction.

**`WorkflowDefinition.__post_init__` gains one new validation**: every
non-`None` `parallel_group` value's steps must be contiguous --

```python
if group is not None and group != previous_group and group in seen_groups:
    raise WorkflowError(
        f"WorkflowDefinition.steps: parallel_group {group!r} must be "
        "contiguous (all its steps adjacent in `steps`)."
    )
```

A definition that never sets `parallel_group` trivially satisfies this
(every step's group is `None`) -- **zero behavior change for any existing
`WorkflowDefinition`.**

**A parallel unit's steps all receive the identical `WorkflowContext`
snapshot** -- the one from immediately *before* the unit started,
reflecting only prior units' results, **never** a sibling's result from
the same, currently-running unit. This is the load-bearing design
decision that makes dynamic steps and parallel execution compose safely
together with zero locking: since `WorkflowContext` is immutable and
handed to every sibling read-only, and no sibling can observe another
sibling's in-flight or completed result until the *next* unit begins,
there is no data race to construct, coordinate around, or document away
-- it is structurally impossible by this design, not merely
discouraged. (A later step, in a *subsequent* unit, sees the whole
group's results, exactly as the Sprint-30 integration test requires --
see Part D below.)

**Concurrency mechanism: `concurrent.futures.ThreadPoolExecutor`, scoped
to exactly one unit, per call, with `with` (guaranteeing shutdown before
the unit's results are used).** Rejected `asyncio` outright -- see
"Alternatives considered." This is genuinely "structured concurrency" in
the plain sense the sprint asks for: bounded lifetime (never outlives one
`_run_parallel_group` call), no persistent pool, nothing that survives
`run()` returning, no thread ever left running or dangling after the
method that created it exits.

**Execution ordering**: every step in a unit is submitted to the executor
before any is awaited; genuinely concurrent, no defined start order among
siblings. **Result ordering is nonetheless fully deterministic**: results
are collected as futures complete (`concurrent.futures.as_completed`,
necessarily in wall-clock order, which is *not* deterministic run to
run), but the unit's contribution to `step_results` is then **rebuilt by
iterating the unit in its original, declared order** and pulling each
step's already-known result from the completion-order collection. The
`dict` a caller ultimately sees in `WorkflowResult.step_results` therefore
has the same key-insertion order on every run, regardless of which
sibling happened to finish first on that particular run.

**Failure propagation, one branch**: a step's own semantic failure
(`ExecutionResult(success=False, ...)`, not a raise) is folded into the
unit's results exactly like any sequential step's; whether it stops the
*workflow* is decided by the same `continue_on_failure` rule as today,
evaluated once the whole unit is known, against the **first** such
stopping failure in the unit's *declared* order (not completion order --
completion order is not a fact any public result may depend on).

**Failure propagation, multiple branches, and unexpected raises**: if
`execution_engine.execute(...)` itself *raises* for one sibling (finding
5 -- rare, but not impossible), that exception is re-raised from
`WorkflowEngine.run()` **exactly as it would be for a single sequential
step that raises today** -- preserving finding 5's existing behavior
exactly, for a unit of size one *or* larger. If **more than one** sibling
raises within the same unit, they are collected and raised together as a
single builtin `ExceptionGroup` (PEP 654, unconditionally available --
`pyproject.toml` already requires Python ≥3.12), in declared order, so
no failure is silently dropped merely because it happened to run
alongside another. No new kernel exception type was invented for this --
`ExceptionGroup` is the standard-library-correct tool for exactly this
situation, and using it is the smallest possible design, not a new
abstraction.

**Partial completion / cancellation**: once the *first* stopping failure
(`success=False` and `continue_on_failure=False`) is observed among a
unit's already-completed siblings, every **not-yet-started** sibling
future in that same unit is cancelled via `Future.cancel()` -- a real,
well-defined standard-library capability ("returns `True` if the call was
successfully cancelled... `False` if it is currently executing or has
already finished"). This is honest, best-effort cancellation, not a
guarantee: a sibling already running when the stopping failure is
observed runs to completion regardless (Python cannot forcibly interrupt
a running thread, and this sprint does not attempt to). Cancellation is
most visible, and most valuable, when `max_concurrency` (below) is set
below the unit's size, so some siblings are genuinely still queued rather
than already running. A cancelled sibling never appears in that run's
`step_results` at all -- it never executed, the same absence
`test_early_stop_prevents_later_steps_from_running` already asserts for
a step sequentially *after* a stopping failure.

**Concurrency limit**: `WorkflowEngine.__init__` gains one new, keyword-
only, optional parameter, `max_concurrency: int | None = None`
(`WorkflowError` if given `<= 0`). `None` (the default) means unbounded
for a given unit -- every step in that unit is submitted to the executor
at once (`max_workers=len(unit)`). Applies uniformly as the cap for
every parallel unit this engine instance ever runs; it is not
per-step or per-group, keeping the surface area to exactly one new
constructor argument.

**Context mutation rules**: covered above -- a unit's `WorkflowContext`
is shared, read-only, and identical across every sibling; no sibling can
mutate it in a way any other sibling, or any later step, would observe
(frozen dataclass; each context replacement is a distinct object).

**Thread/async safety assumptions -- the one real, new precondition this
sprint introduces.** `ExecutionEngine.execute()` (finding 6) is safe to
call concurrently from multiple threads *only if its own injected
`Dispatcher`/`Authorizer`/`EventBus`/`MemoryStore`/`StructuredEventSink`
are*. This was never previously a concern -- pre-Sprint-30
`WorkflowEngine` only ever called `execute()` from one thread, serially.
Stated plainly, not hidden in a footnote:

- `InMemoryStore`/`InMemoryEventBus` are backed by a plain `dict`/`list`
  with no internal locking. Under CPython's GIL, individual
  operations (a `dict.__setitem__`, a `list.append`) cannot corrupt
  memory, so concurrent use will not crash -- but neither is declared,
  tested, or guaranteed thread-safe by this or any prior ADR; ordering
  across concurrent writers is not specified.
- **`SQLiteMemoryStore` ([ADR-0021](0021-persistent-memory-sqlite-store.md))
  is explicitly *not* safe** to share across threads --
  `sqlite3.connect(..., check_same_thread=True)` (its documented,
  deliberate default) raises if used from a thread other than the one
  that created it. A caller who configures an `ExecutionEngine` with a
  shared `SQLiteMemoryStore` **and** drives it through `WorkflowEngine`
  parallel units **will** hit this. This is not a defect Sprint 30
  introduces into `SQLiteMemoryStore` -- it is a real, pre-existing,
  correctly-documented property of that store that a new *caller*
  (parallel `WorkflowEngine`) can now, for the first time, actually
  violate. The fix is the caller's: do not share a single
  `SQLiteMemoryStore`-backed `ExecutionEngine` across parallel workflow
  steps; use `InMemoryStore`, a separate store per thread, or avoid
  `parallel_group` for steps whose `ExecutionEngine` is so configured.
  Documented here and in `docs/specs/workflow.md` so this is discovered
  by reading, not by a production `sqlite3.ProgrammingError`.

Parallel execution is opt-in per the caller explicitly setting
`parallel_group`; a caller who never does never encounters any of the
above, on any store.

### C. Scheduling

**What "scheduling" correctly means inside this kernel, decided before
any implementation**: per this sprint's own explicit boundary (no
external queues/brokers/cron/daemons, no long-running scheduler service,
no persistent job queue, no import-time scheduler, no hidden polling
loop, no uncontrolled background thread), **the kernel cannot and does
not own making a workflow run happen at a future wall-clock moment.**
That is, and remains, an external-runtime responsibility -- a cron job, a
task queue, an orchestrator, or a human, invoking `WorkflowEngine.run()`
again later. What the kernel *can* correctly own, entirely within its
existing synchronous, in-process, no-daemon boundary, is:

1. **Declarative, inspectable "not before" metadata** on a step
   (`WorkflowStep.not_before: datetime | None = None`) -- a fact an
   external scheduler could read off a `WorkflowDefinition` without the
   kernel exposing any new scheduling API for it.
2. **A deterministic, injectable-clock-based *guard*** so that if
   `run()` *is* invoked before a step's time (an external scheduler
   firing early, clock skew, a caller not checking first), the kernel
   correctly declines to execute that step rather than silently running
   it anyway -- without ever blocking, sleeping, or spawning anything.

**`Clock`, a new, minimal `Protocol`** (`workflow/clock.py`):

```python
@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
```

`WorkflowEngine.__init__` gains one new, keyword-only, optional
parameter, `clock: Clock | None = None` -- `None` (the default)
constructs a `SystemClock()` **inside `__init__`, at object-construction
time, never at import time** (no module-level singleton, no clock
created merely by `import mellivor_kernel.workflow`).

**Enforcement, per step, evaluated immediately before that step (or its
containing unit) would otherwise run**: if `step.not_before` is set and
`self._clock.now() < step.not_before`, the kernel synthesizes a failed
`ExecutionResult` --

```python
ExecutionResult(
    success=False,
    error=(
        f"Step {step.name!r} is not yet due to run "
        f"(not_before={step.not_before.isoformat()}, now={now.isoformat()})."
    ),
    metadata={"stage": "scheduling"},
)
```

-- flowing through **the exact same** `continue_on_failure`/stop/
memory/event machinery as any other step outcome, reusing the identical
mechanism Part A's dynamic-request failures already established. No new
`WorkflowResult` field, no new "pending"/"deferred" run state, was added
-- a not-yet-due step is a normal, typed failure a workflow author
handles the same way as any other (`continue_on_failure=True` to soft-
skip it and let the rest of the run proceed; `False`, the default, to
have it hold the whole run at that point until re-invoked later, by
whatever external mechanism decided to invoke `run()` at all).

**`not_before` is checked before `request`/`request_factory` is
resolved** -- if a step is not yet due, its (possibly side-effecting)
`request_factory` is never called at all.

**Immediate execution**: a step with no `not_before` (the default,
every existing step) is entirely unaffected -- the check is skipped.

**Past/invalid schedule behavior**: a `not_before` at or before
`clock.now()` never blocks a step -- the same `nbf`-style semantics
JSON Web Tokens already use for the same field name's meaning elsewhere
in the industry: "not before," never "exactly at." `WorkflowStep.__post_init__`
gains one new validation: a set `not_before` **must be timezone-aware**
(`tzinfo is not None`), raising `WorkflowError` otherwise -- an
ambiguous, naive datetime being silently compared against a UTC-aware
`clock.now()` is exactly the kind of "invalid... schedule behavior" this
ADR must define rather than leave to accident.

**Cancellation before scheduled execution**: satisfied structurally by
ordering alone -- a not-yet-due step's guard check happens *before* it is
ever submitted to a parallel unit's executor (Part B) or dispatched to
`ExecutionEngine` at all, so "cancelling" it costs nothing and requires
no new mechanism: it was simply never started.

**No uncontrolled background thread, no hidden polling loop, no import-
time scheduler creation, no real-time dependency in tests**: all four
are satisfied by construction -- there is no thread, no loop, no timer,
anywhere in this design; `Clock` exists specifically so every scheduling
test injects a fake, controllable `now()` and asserts instantly, with
zero real sleeps, ever.

**What scheduling explicitly does NOT provide**, stated as plainly as
Part B's security limitation was: this kernel does not run a workflow
"in 6 hours" by itself. It does not persist a not-yet-due step across
process restarts beyond whatever `memory` already, independently,
provides (unchanged by this sprint). It does not retry, poll, or wake
itself up. A product that wants true durable, wall-clock-triggered
workflow execution must supply the external trigger (cron, a task
queue, an orchestrator) itself; this kernel's contribution is the
metadata that trigger can read, and the guard that protects correctness
if it fires early.

## Architecture stop conditions -- explicitly checked, none triggered

- No existing public field changes meaning. `request`'s *type* widens
  (`ExecutionRequest` -> `ExecutionRequest | None`); its meaning when set
  is unchanged.
- No existing required constructor signature breaks -- every call site in
  this repository uses keyword arguments (finding 2); `WorkflowEngine`'s
  new parameters are keyword-only with defaults.
- No existing sequential semantics change -- proven, not merely argued,
  by the entire pre-existing `tests/workflow/test_engine.py` suite
  passing unmodified.
- Dynamic steps require no unsafe evaluation -- `request_factory` is a
  plain caller-supplied callable, never interpreted or evaluated by the
  kernel.
- Parallelism requires no hidden global state -- `ThreadPoolExecutor` is
  created and torn down within a single `_run_parallel_group` call;
  nothing module-level, nothing surviving `run()`.
- Scheduling requires no daemon or persistent worker -- see Part C in
  full; there is none.
- No existing frozen public type is mutated in a breaking way -- every
  type remains frozen; every change is an additive field.
- No MAJOR-version SemVer change is required -- every change here is
  MINOR-compatible per [ADR-0005](0005-versioning-strategy.md), the
  same class of change Sprints 27–29 already made.

## Alternatives considered

- **A template/expression-string mechanism for dynamic steps** (e.g.
  `"{{steps.first.payload.field}}"` substituted into a request). Rejected
  per this sprint's explicit instruction ("avoid introducing a template
  language unless strictly necessary") and because it would require the
  kernel to parse and evaluate a mini-language against workflow state --
  exactly the "arbitrary... evaluation" surface a plain callable avoids
  entirely, for no expressive benefit over Python itself.
- **A full dependency-graph (DAG) model for parallel steps**, with
  explicit per-step `depends_on: frozenset[str]` edges and a topological
  scheduler. Rejected: significantly larger design and validation surface
  (cycle detection, partial-order execution, cross-group dependencies)
  for a v1.1 scope explicitly bounded away from "distributed
  orchestration." The contiguous-group model expresses everything this
  sprint's own examples need ("dynamic result use → parallel execution →
  downstream sequential step") with far less surface area; a DAG model
  remains available as a future, separately-scoped extension if a
  concrete need for cross-group partial dependencies is ever established.
- **`asyncio`-based parallel execution** (making `WorkflowEngine.run`, or
  a new `arun`, a coroutine; running steps via `asyncio.gather`).
  Rejected outright: `ExecutionEngine.execute()` and everything beneath
  it (`Dispatcher`, `ToolExecutionPipeline`, every `BaseProvider`/
  `BaseTool`) is synchronous, unconditionally, throughout the kernel
  (finding 4) -- introducing `asyncio` here would mean either (a) wrapping
  every synchronous call in `asyncio.to_thread`, which is `ThreadPoolExecutor`
  with strictly more ceremony and a new sync/async boundary for the rest
  of the kernel to eventually reconcile with, for zero behavioral gain,
  or (b) making `ExecutionEngine.execute()` itself async, an actual
  breaking change to the kernel's single most-depended-on method (finding
  from ADR-0019's own responsibility table: "the most exercised contract
  in the kernel... across 23 sprints, with zero contract changes ever
  required") that this ADR's own stop conditions forbid without an
  explicit, separate decision. `ThreadPoolExecutor` matches "structured
  concurrency appropriate to the repository's current execution model"
  literally, at zero cost to every existing synchronous caller.
- **A background thread or timer that wakes and runs a step when its
  `not_before` arrives.** Rejected outright, per this sprint's explicit
  constraints (no uncontrolled background thread, no hidden polling
  loop). Also rejected: **blocking (`time.sleep`) inside `run()` until
  `not_before` arrives.** Considered seriously -- it would still be
  "structured" (no thread survives the call) and would let a single
  `run()` invocation transparently "wait out" a short delay. Rejected
  because a kernel meant to be embedded in-process (ADR-0004,
  "library-first, in-process") has no way to bound how long a caller's
  thread might be blocked -- a `not_before` set hours out would silently
  freeze the calling thread for hours, which is a worse citizen inside a
  host application's process than declining to run and returning control
  immediately. The guard-and-return design gives the caller (and any
  external scheduler layered on top) that control back explicitly,
  instead of the kernel silently claiming it.
- **A `WorkflowResult`/`ExecutionResult` "pending" or "deferred" status**
  distinct from success/failure, for a not-yet-due or cancelled step.
  Rejected: it would require widening `ExecutionResult.success: bool` to
  a three-state enum or adding a new field to an already-frozen,
  extensively depended-upon type, a materially larger and riskier change
  than reusing the existing `success=False` + `metadata["stage"]`
  pattern `Dispatcher`/`ToolExecutionPipeline` already established for
  exactly this kind of "didn't succeed, but not a generic failure either"
  distinction.
- **Widening `WorkflowDefinition.steps`'s type to accept a structural
  protocol or a second step-like class**, rather than adding fields to
  the existing `WorkflowStep`. Rejected: would touch an existing field's
  declared type more invasively than necessary, and would force every
  consumer of `steps` (including `WorkflowDefinition.__post_init__`'s own
  duplicate-name check) to handle two shapes. Additive fields on the one
  existing type is strictly smaller.

## Consequences

- `WorkflowStep` gains three new optional fields
  (`request_factory`, `parallel_group`, `not_before`) and widens
  `request`'s type to `ExecutionRequest | None`; `WorkflowDefinition`
  gains one new construction-time validation (`parallel_group`
  contiguity); `WorkflowEngine.__init__` gains two new keyword-only
  parameters (`max_concurrency`, `clock`). `workflow.__all__` gains two
  new names, `Clock` and `SystemClock`. Every other public name in
  `mellivor_kernel.workflow` is unchanged. All MINOR-compatible per
  ADR-0005.
- A workflow that uses none of the new fields/parameters is, by
  construction and by test, observably identical to a Sprint-12-era
  workflow -- same events, same memory records, same `WorkflowResult`
  shape, same exceptions, same thread (the calling one, only).
- `workflow` gains no new dependency, third-party or otherwise --
  `concurrent.futures`, `ExceptionGroup`, and `datetime` are all standard
  library, already available at the kernel's `>=3.12` floor.
- A caller combining `SQLiteMemoryStore` with parallel `WorkflowEngine`
  steps must now read and respect the thread-safety note in Part B --
  this is a genuinely new caller-facing precondition Sprint 30
  introduces, documented here and in `docs/specs/workflow.md`, not
  silently left for a caller to discover as a runtime crash.
- Sprint 31 (v1.1 Release Gate) inherits a workflow subsystem whose
  compatibility promise is exactly: everything ADR-0010/ADR-0019 already
  covered, unchanged, plus these three new, fully optional capabilities.
