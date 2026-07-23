# `agents` subsystem spec

Status: Implemented (Sprint 13A) — Agent Runtime Core: a single agent
invoking a single workflow. No planning, reasoning, reflection, or
multi-agent composition.

Public contract exported from `mellivor_kernel.agents`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0011](../adr/0011-agent-runtime-core-and-orchestration-chain.md) for
why this subsystem exists and the orchestration chain it extends.

## Exceptions

`agents/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `AgentError` — the only exception this subsystem raises, and only for
  invalid data (a malformed `AgentDefinition` or `AgentResult`). A
  workflow failing during a run is never an exception — it is a normal
  outcome captured in `AgentResult`.

## `AgentDefinition`

An immutable (`frozen=True, slots=True`) dataclass — the reusable
"recipe":

```python
name: str
workflow: WorkflowDefinition
metadata: Mapping[str, object] = field(default_factory=dict)
```

Deliberately thin: names exactly one `workflow.WorkflowDefinition` to
invoke. No dynamic workflow selection, no sequencing of multiple
workflows. `__post_init__` rejects a blank `name`, raising `AgentError`.

## `Agent`

An immutable (`frozen=True, slots=True`) dataclass — a single, identified
run of an `AgentDefinition`:

```python
definition: AgentDefinition
agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

`agent_id` is auto-generated (a UUID4 string) if not supplied, the same
convention `workflow.Workflow.workflow_id` and
`execution.ExecutionRequest.request_id` use, for log/event/memory
correlation.

## `AgentContext`

An immutable (`frozen=True, slots=True`) dataclass:

```python
workflow_context: WorkflowContext
```

Deliberately thin — just the `workflow.WorkflowContext` passed to
`WorkflowEngine.run()` when this agent's workflow is invoked. Nothing
else needs sharing at this sprint's scope, since an agent run invokes
exactly one workflow (no accumulating state across multiple invocations,
unlike `WorkflowContext.step_results` across multiple steps).

## `AgentResult`

An immutable (`frozen=True, slots=True`) dataclass — the outcome of one
`AgentEngine.execute()` call:

```python
success: bool
workflow_result: WorkflowResult
error: str | None = None
```

`success` mirrors `workflow_result.success` directly — an agent's only
job is invoking its one workflow, so it succeeds exactly when that
workflow does. `workflow_result` is always present (required, not
optional): `WorkflowEngine.run()` never raises for a normal failure, so
there is always a concrete result to report, on success or failure alike.
`__post_init__` enforces: `success=False` requires a non-empty `error`;
`success=True` forbids `error`. Violating either raises `AgentError`.

## `agents.events`

Three of `agents`' own event types (`events.Event` subclasses), published
by `AgentEngine`, not part of the generic `events` package — the same
reasoning `execution.events`/`authorization.events`/`workflow.events`
already follow (ADR-0008):

- `AgentStarted` (`agent_id`, `name`) — published once, at the start of
  `execute()`.
- `AgentCompleted` (`agent_id`, `name`) — published when the invoked
  workflow completes without being stopped early.
- `AgentFailed` (`agent_id`, `name`, `error`) — published when the
  invoked workflow stops early.

Exactly one of `AgentCompleted`/`AgentFailed` is published per
`execute()` call, always preceded by `AgentStarted`.

## `AgentEngine`

The orchestration entry point.

```python
def __init__(
    self,
    workflow_engine: WorkflowEngine,
    *,
    memory: MemoryStore | None = None,
    event_bus: EventBus | None = None,
) -> None

def execute(self, agent: Agent, context: AgentContext) -> AgentResult
```

All infrastructure is received via dependency injection — `AgentEngine`
never constructs a `WorkflowEngine`, a memory backend, or an event bus
itself. Notably, `AgentEngine` never imports `execution`, `authorization`,
`tools`, or `providers` at all — the orchestration chain is enforced not
just by convention but by the fact that nothing in `agents/` has the
import available to reach around `WorkflowEngine`.

- Logs the start of the run and publishes `AgentStarted`.
- Wraps `agent.definition.workflow` in a fresh `workflow.Workflow` run and
  delegates entirely to `workflow_engine.run(workflow, context.workflow_context)`.
  `AgentEngine` never touches a tool, provider, `Dispatcher`, or
  `ExecutionEngine` directly.
- If the workflow succeeds, publishes `AgentCompleted` and returns a
  successful `AgentResult`.
- If the workflow fails (stopped early — see `docs/specs/workflow.md`),
  publishes `AgentFailed` (`error` naming the failed workflow and its own
  error) and returns a failed `AgentResult`.
- Records the outcome to memory (if configured) either way. A
  `memory.add()` failure is caught and logged, never propagated — a
  misbehaving `MemoryStore` must never break an agent run, the same
  guarantee `WorkflowEngine`/`ExecutionEngine` already give.

With `event_bus=None`/`memory=None` (both default), no events are
published and nothing is recorded — identical to an `AgentEngine`
constructed with only `workflow_engine`.

## The orchestration chain

```
Agent -> Workflow -> Execution -> Tool/Provider
```

Each layer delegates entirely to the one below it and never reaches
around it:

- `AgentEngine.execute()` only ever calls `WorkflowEngine.run()`.
- `WorkflowEngine.run()` only ever calls `ExecutionEngine.execute()`
  (see `docs/specs/workflow.md`).
- `ExecutionEngine.execute()` only ever calls `Dispatcher.dispatch()`
  (see `docs/specs/execution.md`).

## Dependency relationship

```
agents → workflow, memory, events
```

`agents` depends on `workflow` (`Workflow`, `WorkflowContext`,
`WorkflowDefinition`, `WorkflowEngine`, `WorkflowResult`), `memory`
(`MemoryEntry`, `MemoryStore`), and `events` (`Event`, `EventBus`) —
normal dependencies on generic infrastructure and on the next layer down
in the orchestration chain. `agents` has **no** dependency on `execution`,
`authorization`, `tools`, or `providers` — it never needs to, since every
step ultimately delegates through `workflow`. `workflow` (and everything
it depends on) has **no** dependency on `agents`, and never will — see
ADR-0011.
