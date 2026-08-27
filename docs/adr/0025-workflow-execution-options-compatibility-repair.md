# 0025. Preserve WorkflowStep v1.0 through external execution options

Status: Accepted
Date: 2026-08-27

## Context

ADR-0024 implemented Sprint 30 by adding `request_factory`, `parallel_group`,
and `not_before` fields to the public, frozen `WorkflowStep` dataclass and by
making its required `request: ExecutionRequest` field optional. The Sprint 31
release audit correctly rejected that surface under ADR-0005: it changed the
constructor signature, annotations, dataclass fields, representation,
equality/hash inputs, `dataclasses.asdict()` shape, and the static type of
`step.request`. Defaults preserved many runtime call sites, but they did not
preserve the v1.0 public contract frozen in Sprint 25.

The v1.1 target must remain a MINOR release. Dynamic request construction,
opt-in parallel execution, and scheduling eligibility remain approved Sprint
30 functionality, so they need a genuinely additive home outside the frozen
dataclass.

## Decision

Restore `WorkflowStep` byte-for-contract to its v1.0 public shape:

```python
@dataclass(frozen=True, slots=True)
class WorkflowStep:
    name: str
    request: ExecutionRequest
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    continue_on_failure: bool = False
```

Add the frozen, slotted `WorkflowExecutionOptions` value and the public
`RequestResolver` alias. `WorkflowEngine.run()` accepts one new optional,
keyword-only `options` argument. With no options, the original sequential path
and all v1.0 semantics are unchanged.

`WorkflowExecutionOptions` contains:

- `request_resolvers`: step-name to a callable accepting the accumulated
  immutable `WorkflowContext` and that step's original `ExecutionRequest`, and
  returning an `ExecutionRequest`;
- `parallel_groups`: ordered tuples of contiguous step names which explicitly
  opt those steps into concurrent execution; and
- `not_before`: step-name to a timezone-aware eligibility timestamp.

The original request is always present and remains meaningful. A resolver can
derive a replacement request from prior results while using the original as a
typed base. There is no expression language, string evaluation, or template
DSL. Missing prior results and resolver exceptions become bounded workflow
failures through the existing dynamic-request error boundary.

The engine snapshots all supplied mappings before execution, validates that
every referenced name exists, and validates that parallel groups are
contiguous and in workflow declaration order. Parallel siblings receive the
same pre-group context; their results are folded in declaration order.
Scheduling remains a check-only `not_before` primitive using the injected
`Clock`; Kernel does not sleep, poll, persist jobs, or own a daemon.

`max_concurrency`, `Clock`, and `SystemClock` remain the additive Sprint 30
engine APIs established by ADR-0024. Their optional/keyword-only construction
does not modify an existing public type's fields or existing call semantics.

## Compatibility audit

Against the v1.0 tag, `WorkflowStep` again has the same:

- positional and keyword constructor signature;
- required `request: ExecutionRequest` annotation;
- dataclass field order and defaults;
- generated `repr`, equality, and hash participation;
- `dataclasses.asdict()` keys and nesting;
- frozen/slotted behavior and ordinary subclassing expectations; and
- runtime and strict-static-typing behavior, including
  `step.request.operation` without narrowing.

`WorkflowDefinition` also returns to its v1.0 field schema and validation.
Execution metadata is external, so serialization or introspection of existing
workflow definitions does not acquire v1.1 fields.

Adding an exported type and an optional keyword-only argument is additive
under ADR-0005. No existing field changes type or meaning. This is compatible
with a v1.1.0 release.

## Consequences

- Existing workflows and callers require no changes.
- Dynamic, parallel, and scheduled behavior is explicit per invocation rather
  than embedded in serializable workflow definitions.
- One definition can be run with different execution options without mutation.
- Options reference steps by their already-unique names; renaming a step also
  requires updating the caller's options.
- A shared `SQLiteMemoryStore` connection is still unsupported across parallel
  branches because standard SQLite connections retain same-thread behavior.
- ADR-0024 remains historical design context but its direct-`WorkflowStep`
  public surface is superseded by this decision.

## Alternatives considered

### Separate DynamicWorkflowStep subclass

Rejected. A heterogeneous step union would spread branching through definition
and engine APIs and would complicate serialization and consumer typing.

### Add optional metadata fields to WorkflowStep

Rejected. Even optional fields alter the frozen dataclass signature,
introspection, repr/equality/hash participation, and `asdict()` shape.

### Keep request optional and rely on runtime validation

Rejected. It breaks the required constructor contract and forces every v1.0
consumer to narrow `step.request` before ordinary access.

### Template strings or expression evaluation

Rejected. They add a DSL, unsafe evaluation risk, and ambiguous value/type
semantics where typed callables are sufficient.
