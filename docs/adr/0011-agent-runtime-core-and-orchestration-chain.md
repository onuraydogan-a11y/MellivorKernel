# 0011. Agent Runtime Core, and the full orchestration chain

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names
**Agent lifecycle** as a fixed kernel responsibility with a reserved
package (`agents/`) since Sprint 1, but no implementation — the same
situation `events`, `memory`, and `workflow` were in before Sprints 9, 11,
and 12
([ADR-0008](0008-event-bus-and-lifecycle-events.md),
[ADR-0009](0009-memory-subsystem-and-execution-recording.md),
[ADR-0010](0010-workflow-engine-and-orchestration-boundary.md)). This
sprint implements a first, deliberately minimal slice of it:
`AgentEngine` invokes exactly one workflow per run by delegating entirely
to `WorkflowEngine`.

This requires an ADR on the same two counts as ADR-0010: it introduces a
new subsystem with three new dependency edges at once
(`agents → workflow`, `agents → memory`, `agents → events`), and it
extends the orchestration/execution boundary ADR-0010 fixed with one more
link: Agent → Workflow → Execution → Tool/Provider, one direction only,
permanently.

## Decision

**A new top-level package, `src/mellivor_kernel/agents/`,** coordinates
existing kernel subsystems — it does not replace them, and it is
orchestration only:

- `AgentDefinition` — an immutable, reusable "recipe": a `name`, the one
  `workflow.WorkflowDefinition` this agent invokes, and free-form
  `metadata`. Deliberately thin: no planning, no reasoning, no reflection,
  no multi-agent composition. An agent does not choose or sequence
  workflows dynamically; it always runs the one it was configured with.
- `Agent` — a single, identified *run* of an `AgentDefinition`
  (`agent_id`, auto-generated) — the same "definition vs. run" split
  `workflow.Workflow` already establishes for `WorkflowDefinition`.
- `AgentContext` — deliberately thin: just the
  `workflow.WorkflowContext` passed to `WorkflowEngine.run()`. Nothing
  else needs sharing at this sprint's scope, since an agent run invokes
  exactly one workflow.
- `AgentResult` — `success` mirrors `workflow_result.success` directly:
  an agent's only job is invoking its one workflow, so it succeeds
  exactly when that workflow does. `workflow_result` is always present
  (required, not optional) — `WorkflowEngine.run()` never raises for a
  normal failure, so there is always one to report. Same invariant-
  validating `__post_init__` pattern as `WorkflowResult`/`ExecutionResult`.
- `AgentEngine` — `execute(agent, context) -> AgentResult`: wraps
  `agent.definition.workflow` in a fresh `workflow.Workflow` run and
  delegates entirely to `self._workflow_engine.run(...)`. Publishes
  `AgentStarted` once, then exactly one of `AgentCompleted`/`AgentFailed`,
  and records its own outcome to memory — all via constructor-injected
  `EventBus`/`MemoryStore` (optional, `None` by default, no behavior
  change if unconfigured), the identical pattern `WorkflowEngine` and
  `ExecutionEngine` already use.
- `AgentError` — raised only for invalid data (a malformed
  `AgentDefinition`/`AgentResult`); a workflow failing during a run is a
  normal, non-raising outcome captured in `AgentResult`.

**`AgentEngine` receives `WorkflowEngine`, `MemoryStore`, and `EventBus`
entirely via constructor injection** — it never constructs any of the
three itself. Notably, `AgentEngine` never even imports `execution`,
`authorization`, `tools`, or `providers` — the chain is enforced not just
by convention but by the fact that nothing in `agents/` has the import
available to reach around `WorkflowEngine` even if it wanted to.

**Memory and events: the identical pattern as `workflow`, one level up.**
`AgentEngine` records a run-level summary (`agent_id`, name, success)
after every run, through the same `MemoryStore` a caller can read back
from directly — proven in the integration test, not merely asserted.
`AgentStarted`/`AgentCompleted`/`AgentFailed` are `agents`' own event
types (`agents/events.py`), not part of the generic `events` package —
the same reasoning that keeps `execution.events`/`authorization.events`/
`workflow.events` out of it (ADR-0008): `events` stays free of any
knowledge of "agent" as a concept.

**No planning, no reasoning, no reflection, no multi-agent, exactly as
instructed.** This sprint's `AgentDefinition` is a static pointer to one
workflow; it does not decide *which* workflow to run, does not sequence
multiple workflows, and does not coordinate multiple agents. Those are
all real design decisions requiring their own ADR once a concrete need
for them exists.

## Alternatives considered

- **Let `AgentEngine` call `ExecutionEngine` (or `Dispatcher`, or a tool/
  provider) directly**, bypassing `WorkflowEngine` for a "simple" single-
  step agent. Rejected: the sprint's explicit premise is that Agent Runtime
  is orchestration only, and the chain Agent → Workflow → Execution →
  Tool/Provider is fixed in one direction. A single-step agent is
  expressed as a one-step `WorkflowDefinition` — no shortcut needed, and
  none added.
- **Give `AgentContext` its own accumulating state** (mirroring
  `WorkflowContext.step_results`), for a hypothetical future multi-
  workflow agent. Rejected for this sprint: there is exactly one workflow
  invocation per agent run, so there is nothing to accumulate yet;
  inventing the field now would be exactly the kind of placeholder this
  sprint's instructions (and this kernel's principles) reject.
- **Make `AgentResult.workflow_result` optional (`| None`).** Rejected:
  `AgentEngine.execute()` always has a concrete `WorkflowResult` by the
  time it builds an `AgentResult` — `WorkflowEngine.run()` doesn't raise
  for a normal failure — so making the field optional would only invite
  a meaningless `None` case that can never actually occur.
- **Make `memory`/`event_bus` required constructor arguments.** Rejected
  for the same reason ADR-0009/ADR-0010 already gave: optional-with-a-
  safe-default costs nothing and matches every other engine in the
  kernel. `workflow_engine` itself is required — an `AgentEngine` with
  nothing to delegate to cannot do anything.

## Consequences

- `execution`, `authorization`, `memory`, `events`, `tools`, `providers`,
  `bootstrap`, and `workflow` are all byte-for-byte unchanged by this
  sprint — verified by the entire prior test suite (447 tests including
  this sprint's own) passing unmodified before and after. `agents` is the
  only new dependency edge, and it points one way only, through
  `workflow`.
- `workflow` (and everything it depends on) must never import `agents` —
  this ADR fixes that direction as a permanent constraint, the same kind
  of guarantee ADR-0010 gave for `execution`/`workflow`.
- A future multi-agent, planning, or reasoning capability is understood
  to be additive on top of this sprint's `AgentDefinition`/`AgentEngine`,
  not a replacement for them — each requiring its own design decision (and
  likely its own ADR) once a concrete need is established.
