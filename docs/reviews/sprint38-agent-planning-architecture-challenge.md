# Sprint 38: Agent planning, reasoning, and execution boundary

Status: Architecture Challenge complete — defer; insufficient consumer need

Date: 2026-09-02

## Decision

**E — DEFER: INSUFFICIENT CONSUMER NEED.**

Mellivor Kernel must not add planning contracts, an autonomous loop, a second
execution model, or reasoning/reflection storage now. The existing runtime
already supplies the generic deterministic substrate: an agent delegates to a
workflow; a workflow composes execution requests; and every request passes
through authorization and the single dispatcher before reaching a tool or
provider.

No current consumer demonstrates a need for runtime plan generation.
Mellivor One's current Agent Catalog uses fixed application-owned workflows.
Mellivor AI Security owns agent identity, delegated-authority, and tool-call
security policy but does not request a planner. Creating generic types without
a consumer would freeze guesses about goals, plan validation, approval,
budgets, provider output, and completion semantics.

If evidence later justifies planning, the first architecture to test is an
injected, model-independent planner that produces the existing
`WorkflowDefinition`, followed by normal `WorkflowEngine` execution. That is a
research direction, not an approved contract. Multi-agent coordination remains
separate Future Research.

## Scope and evidence

The review covers ADR-0002/0003 boundaries, ADR-0005 SemVer, ADR-0006 through
ADR-0013 execution/authorization/events/memory/workflow/agents/observability,
ADR-0018 composition, ADR-0019/0020 release scope, ADR-0025 workflow
compatibility, the current packages and tests, the Future Research roadmap,
and Sprint 34–37 decisions. Read-only consumer evidence came from the sibling
`MellivorOne` and `MellivorAISecurity` repositories.

## Existing agent and execution architecture

### Agent lifecycle

- `AgentDefinition` is an immutable name/description plus exactly one
  `WorkflowDefinition`.
- `Agent` is one identified run of that definition.
- `AgentContext` wraps a `WorkflowContext`; it does not add mutable scratch
  state, goals, messages, prompts, authority, or provider selection.
- `AgentEngine.execute()` constructs a workflow run and delegates it to the
  injected `WorkflowEngine`. It does not execute tools/providers, select a
  workflow, plan, reason, retry, or loop.
- `AgentResult` translates workflow success/failure and retains the
  `WorkflowResult`.
- Agent start/completed/failed events and optional memory summaries observe
  the run. Memory-write failure is logged and swallowed; workflow failure is a
  normal result.

The baseline is intentionally one agent → one workflow. It is a lifecycle
wrapper and correlation boundary, not an autonomous-agent framework.

### Workflow lifecycle

- `WorkflowDefinition` is an immutable ordered recipe of uniquely named
  `WorkflowStep` values.
- Each `WorkflowStep` holds one frozen `ExecutionRequest`, claimed permissions,
  and `continue_on_failure` behavior.
- `WorkflowExecutionOptions` adds per-run request resolvers, explicitly named
  contiguous parallel groups, and timezone-aware `not_before` guards without
  changing the frozen step/definition shape.
- A `RequestResolver` may deterministically construct a step request from the
  immutable workflow context and prior results. It does not add, remove, or
  reorder steps and is not a planner.
- `WorkflowEngine` delegates every resolved request to `ExecutionEngine`.
  Sequential steps run inline; explicit groups use a call-scoped thread pool;
  declared-order results remain deterministic.
- A normal failed result stops at the first declared non-continuable failure.
  Dynamic-resolution and scheduling failures are explicit `ExecutionResult`
  outcomes. Unexpected exceptions retain established propagation behavior.
- Workflow lifecycle events and optional memory summaries are emitted around
  the run.

### Execution, tools, and providers

The single execution path is:

```text
AgentEngine
  → WorkflowEngine
    → ExecutionEngine
      → Authorizer (when configured)
      → Dispatcher
        → ToolRegistry → ToolExecutionPipeline → Tool
        → ProviderRegistry → BaseProvider
```

`ExecutionEngine` validates through immutable request construction, asks the
injected authorizer before dispatch, publishes lifecycle events, emits
structured observations, records an optional memory summary, and returns one
`ExecutionResult`. It deliberately owns no retry or workflow composition.

`Dispatcher` is the only execution component aware of tools and providers. It
resolves a named target, translates lookup/invocation failures, and never
interprets planning policy. The tool pipeline performs tool validation and a
second permission check against the tool's declared permissions before
execution. Provider invocation has no tool permission semantics and remains
behind `BaseProvider`/`ProviderRegistry`.

### State, authorization, and observation

- Context objects pass configuration, logging, runtime, services, and prior
  step results by explicit dependency injection.
- Memory is an optional record/search abstraction, not hidden agent scratch
  state or a conversation/planning store.
- Authorization is checked for each execution request. Workflow/agent
  selection never grants permission.
- Execution, authorization, workflow, and agent lifecycle events are separate,
  correlated observations. Only execution currently emits through the generic
  structured observability sink; other layers publish their typed events.
- Plugins expose caller-supplied extensions and services but do not plan or
  gain implicit execution authority.

These are reusable capabilities a planner would have to reuse, not duplicate.

## Precise planning vocabulary

“Agent planning” is not one capability:

| Concept | Meaning | Current owner/status |
|---|---|---|
| Static workflow definition | A predetermined ordered execution recipe | Kernel already owns it through `WorkflowDefinition` |
| Dynamic request resolution | Construct one declared step's request from earlier results | Kernel already owns it through `WorkflowExecutionOptions.request_resolvers` |
| Runtime plan generation | Produce an executable recipe after a goal/input is known | Not implemented; no approved consumer |
| Task decomposition | Turn a goal into smaller tasks and dependencies | Policy-dependent; no portable semantics demonstrated |
| Tool selection | Choose tools/operations and arguments | Product/shared planner policy; execution still resolves and authorizes the choice |
| Iterative reasoning | Repeatedly use model/output state to choose another action | Not a Kernel primitive; provider/prompt policy |
| Reflection/self-critique | Evaluate an outcome and suggest another action | May be modeled as explicit feedback, but no current contract need |
| Retry | Repeat an equivalent failed operation under a bounded policy | Existing engines deliberately do not own generic retry; semantics depend on idempotency and failure type |
| Replanning | Generate a different recipe after feedback/failure | Loop/planner policy, not execution |
| Goal evaluation | Decide whether product-defined success is achieved | Product policy unless a future consumer proves portable structured criteria |
| Autonomous loop | Repeated plan/execute/observe/replan cycle | Not approved anywhere |

This separation prevents static orchestration, provider prompting, failure
recovery, and autonomy from being collapsed into one vague API.

## Candidate primitive analysis

The conceptual names in the challenge are not justified as Kernel contracts:

| Concept | Why not add it now |
|---|---|
| `Plan` | Duplicates `WorkflowDefinition` unless it carries goals, dependencies, approval, or reasoning policy—none has portable evidence. |
| `PlanStep` | Duplicates `WorkflowStep`/`ExecutionRequest`. A second step type would require conversion and risk bypassing established validation and permissions. |
| `Planner` | A structural producer seam is plausible, but inputs, errors, determinism, model use, and validation cannot be fixed without a consumer. A normal callable can be injected during product experimentation. |
| `PlanningContext` | Existing contexts already carry runtime/configuration and workflow results. Goals, prompt history, budgets, tenant identity, and approvals have materially different ownership and must not be guessed into a generic bag. |
| `PlanningResult` | A successful generated workflow plus failure detail may eventually be useful, but no consumer proves fields or error taxonomy. Existing result patterns are precedent, not evidence. |
| `ExecutionOutcome` | Duplicates `ExecutionResult`, `WorkflowResult`, and `AgentResult` and would obscure which lifecycle produced the outcome. |

No proposed type passes all four tests: it is not already represented, is
reusable across products, is infrastructure rather than policy, and has a
deterministic testable shape proven by use.

## Workflow relationship decision

The alternatives are:

- **A. Produce a `WorkflowDefinition`: strongest future candidate.** It reuses
  immutable steps, dynamic request resolvers, parallel groups, scheduling
  options, failure results, authorization, events, and dispatch. A consumer
  can already construct a definition before creating an `AgentDefinition`.
- **B. Produce a separate execution plan: rejected without evidence.** This
  duplicates workflow representation and invites a second execution engine.
- **C. Dynamically modify an existing workflow: rejected.** Definitions are
  immutable and reusable. Mutation would damage determinism, signatures,
  caching, auditability, and frozen v1.x expectations. Dynamic request
  resolution already covers result-dependent payload construction.
- **D. Remain outside Kernel: current decision.** Products or an experimental
  shared library may generate an ordinary workflow using current APIs.
- **E. Other architecture: no need demonstrated.** A future goal/feedback
  state machine could be evaluated only after a real consumer proves that a
  finite generated workflow cannot represent the need.

If planning is reopened, option A must be dogfooded first. Planning output must
be fully validated before execution, and the resulting workflow must use the
unchanged `WorkflowEngine`/`ExecutionEngine` path. `WorkflowStep`,
`WorkflowDefinition`, `WorkflowExecutionOptions`, `RequestResolver`, parallel
execution, and scheduling remain frozen and must not be modified for planning.

## Provider relationship

- A planner is not inherently a provider. Deterministic/rule-based and model-
  backed planners should be substitutable if a seam is eventually justified.
- A model-backed implementation may consume `BaseProvider` as a dependency; it
  must not extend `BaseProvider` or make planning a provider capability.
- Model selection and provider configuration belong to the consuming
  composition root or shared implementation configuration.
- Planning prompts, tool descriptions exposed to a model, decomposition
  heuristics, completion criteria, and domain guardrails are product/shared-
  library policy, never Kernel constants.
- The planner implementation that understands a model response owns parsing
  and translation. A consumer-owned validator must reject unknown tools,
  malformed operations, unsafe payloads, excessive steps, and policy-invalid
  output before constructing an executable workflow.
- Provider output is untrusted data. Converting it to a workflow conveys no
  authority; each eventual request remains subject to execution authorization.

No BaseProvider change is required or recommended.

## Tool relationship

Tool discovery already exists through `ToolRegistry` and metadata. Selection
does not. That division should remain:

- Registry lookup/discovery, validation, invocation, result translation, and
  permission enforcement are Kernel runtime behavior.
- Which tools are disclosed to a planner, which it prefers, argument policy,
  retry rules, and human approval requirements are consumer policy.
- A selected tool must be represented as a normal `ExecutionRequest` and pass
  through `ExecutionEngine`, the authorizer, `Dispatcher`, and
  `ToolExecutionPipeline`.
- Planner-supplied permissions are never trusted. Authority comes from the
  authenticated/authorized caller and deployment composition, not from plan
  content or model output.
- Tool failure produces the existing explicit result. Retrying or replanning
  must distinguish validation, denial, transient failure, side effects, and
  indeterminate completion; there is no safe universal retry policy.

## Reasoning and reflection boundary

Kernel must not require, request, persist, log, return, or expose chain-of-
thought, hidden reasoning, scratchpads, model deliberation, or self-critique
transcripts. These are neither necessary to execute a plan nor a safe portable
contract.

Observable structured decisions are sufficient: selected operation, validated
arguments, declared dependencies, approval state, outcome category, terminal
reason, and resource usage where a provider reliably supplies it. If future
reflection is useful, it should consume a redacted structured execution or
workflow result and produce an explicit next decision. “Reflection” is then a
planner/policy step, not privileged hidden state and not a new execution path.

## Autonomous loop boundary

Kernel must not currently own:

```text
while goal_not_complete:
    plan
    execute
    observe
    replan
```

The loop belongs in the consuming product today (**C**). A reusable shared
library (**B**) may become appropriate after two products prove common policy.
It does not belong in Kernel (**A**) until evidence isolates generic safety
mechanics from completion and approval policy. “Nowhere yet” (**D**) is the
practical status because no current product has approved such a loop.

Any future loop must be synchronously visible and bounded before starting:

- positive maximum iterations and generated steps;
- wall-clock deadline and per-operation timeout;
- tool-call and provider-call limits;
- token/cost budgets only where usage accounting is reliable, with a hard
  fallback limit that does not depend on it;
- explicit cancellation checked between operations;
- maximum nested planning depth of one unless separately justified;
- terminal statuses for completed, denied, budget exhausted, timed out,
  cancelled, planning failed, execution failed, approval rejected, and
  indeterminate side effect;
- authorization on every execution, including retries;
- human approval before product-classified sensitive or irreversible actions;
- no hidden threads, background loops, recursive engine calls, or import-time
  execution.

These requirements are an evaluation checklist, not approved API fields.

## Security boundary

### Generic Kernel responsibilities already present

- immutable input validation and explicit failure outcomes;
- authorization before every dispatch;
- tool permission enforcement;
- provider/tool exception translation at execution boundaries;
- correlated lifecycle events and structured execution observations;
- dependency injection and no implicit network/runtime behavior; and
- optional backend-neutral memory rather than hidden state.

### Potential shared-library safeguards

- generated-workflow validation against an allowlisted capability snapshot;
- generic hard-limit enforcement for iterations, calls, time, and nesting;
- redaction before feeding tool output back to a model;
- prompt-injection-aware handling of untrusted tool/provider content;
- idempotency classification and retry eligibility; and
- deterministic synthetic planner/loop test harnesses.

These become reusable only after consumer evidence. They must not be silently
inserted into frozen engines.

### Product responsibilities

- authenticated subject and tenant selection;
- goals, prompts, system instructions, domain decomposition, and completion
  criteria;
- tool allowlists, data classification, approval policy, and cost allocation;
- which outputs may be persisted or reintroduced as context;
- tenant-specific memory/context retrieval and retention;
- human escalation/UI; and
- business consequences and recovery for side effects.

Primary risks are unbounded execution, recursive planning, tool abuse,
authorization bypass, prompt injection propagation, poisoned tool output,
resource/cost exhaustion, infinite loops, cross-tenant context leakage, and
unsafe persistence. A planner must never convert untrusted text into authority,
reuse context across tenants, or treat metadata/filtering as authorization.

## Determinism and testability gate

Any future design must be testable without network access or a real model:

- planner behavior is injected through a structural seam or ordinary callable;
- deterministic synthetic inputs produce fixed `WorkflowDefinition` values;
- malformed/oversized/unknown-operation plans fail before execution;
- execution uses fake tools/providers through existing registries;
- clocks, budgets, approval decisions, and cancellation are injected;
- every exit path has an explicit observable outcome;
- no import-time, constructor-time, background, or implicit provider call;
- tests prove each generated request is independently authorized; and
- repeated tests prove stable step/result ordering.

The lack of a concrete consumer means the input/output seam itself cannot yet
be specified responsibly.

## Multi-agent boundary

Multi-agent coordination remains separate Future Research. This review defines
no roles, delegation, agent registry, shared goal, message protocol, supervisor,
consensus, handoff, or cross-agent memory API.

The future direction of generating ordinary workflows does not preclude
multi-agent work because it assumes only that one planner invocation yields one
validated executable recipe. It also does not anticipate multi-agent behavior:
an agent cannot currently be an `ExecutionTarget`, and this review does not
propose making it one. A later multi-agent Architecture Challenge must derive
its own evidence and authority model.

## Ownership classification

### Kernel

- Existing agent/workflow/execution lifecycle contracts.
- Immutable validation, dispatch, authorization hooks, tool permission checks,
  explicit results, events, observations, and backend-neutral memory seams.
- Potential future planning contract only if real consumers prove a minimal
  model-independent seam that generates existing workflows.

### Shared library

- Possible model-backed/rule-based planner implementations.
- Generic workflow-output parsing/validation helpers after multiple consumers
  prove common semantics.
- Possible bounded loop runner and safety-policy toolkit only after reusable
  behavior is demonstrated; never a route around Kernel execution.

### Product

- Goals, prompts, model choice, tool disclosure/selection policy, domain rules,
  completion criteria, retries/replanning, approvals, budgets, tenant mapping,
  context selection, persistence policy, UI, and business-specific behavior.

This classification is deliberately conservative: shared behavior must be
dogfooded before it becomes Kernel surface.

## Compatibility and public API

No types or modules are proposed in Sprint 38. No public API changes are
required. `BaseProvider`, `WorkflowStep`, `WorkflowDefinition`,
`WorkflowExecutionOptions`, `ExecutionTarget`, `Dispatcher`, and `MemoryStore`
remain unchanged.

If later justified, a separate internal experimental module could evaluate one
small structural planner seam returning `WorkflowDefinition`. That could be an
additive v1.x change if it requires no modification to frozen contracts and is
not exported until dogfooded. A new major version is not required by the
architecture direction. Any design that requires changing frozen workflow or
execution behavior must stop for a separate compatibility decision; this
review does not recommend v2.0.

## Rejected current architectures

- A new `Plan`/`PlanStep` graph and execution engine: duplicates workflow and
  risks authorization bypass.
- Mutable workflows: breaks immutable recipes and deterministic execution.
- Planner as a `BaseProvider` extension: conflates model transport with policy.
- Planner as a new `ExecutionTarget`: makes generation look like authority and
  expands a frozen dispatch enum without need.
- Kernel-owned prompts or tool-selection policy: product coupling.
- Chain-of-thought/reflection persistence: unnecessary and unsafe surface.
- Unbounded or hidden autonomous loop: unacceptable enterprise execution risk.
- Combining planning with multi-agent coordination: premature and unscoped.

## Risks and open questions

The main risk of deferral is that products may independently prototype planner
logic. Such experiments must still emit ordinary workflows and use Kernel's
execution path; they should remain product-private until shared evidence
exists.

Questions that only a concrete consumer can answer:

1. What approved goal cannot be represented by a static workflow plus request
   resolvers?
2. Must the full plan be generated before execution, or is a bounded state
   machine genuinely required?
3. Which tool catalog subset can the planner see, and who authorizes it?
4. What plan schema, maximum size, dependencies, and validation errors are
   portable?
5. What are the iteration, call, time, token, cost, and approval limits?
6. Which failures are retryable without duplicating side effects?
7. What structured feedback is safe to return to the planner?
8. How are tenant context, persistence, redaction, and retention enforced?
9. Does a second consumer demonstrate the same seam and policy split?

## Outcome

- Decision: **E — defer; insufficient consumer need**.
- Proposed types/modules: **none**.
- Implementation ADR: **not yet justified**.
- Public API: **unchanged**.
- Stable v1.x compatibility: **preserved**.
- Dependencies/version/UI/code: **unchanged**.
- Next action: obtain Product Owner-approved single-agent planning consumer
  evidence, then run a focused ADR before any internal proof.
