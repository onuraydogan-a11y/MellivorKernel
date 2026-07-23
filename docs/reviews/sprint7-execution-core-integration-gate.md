# Integration Gate #1 — Execution Core

Status: Point-in-time report
Date: 2026-07-23
Scope: Sprint 7. Validates the Execution Core subsystem shipped in Sprint 6
(ADR-0006) against a real, bootstrapped end-to-end use case, per
[CLAUDE.md](../../CLAUDE.md) §14 ("Integration Gates: major milestones
require real end-to-end validation before freezing APIs"). No new
architecture was introduced — this report is descriptive and records what
was proven, what was fixed, and what remains a known gap.

---

## 1. What was validated

Two complete flows, each built entirely from already-public APIs
(`BootstrapBuilder` → `RuntimeContext` → `Dispatcher`/`ExecutionEngine`),
with no internals reached into:

- **Tool Invocation:** `ExecutionRequest(target=TOOL)` →
  `ExecutionEngine.execute()` → `Dispatcher` → `ToolRegistry` +
  `ToolExecutionPipeline` → `ExecutionResult`. See
  `examples/execution_tool_invocation.py` and
  `tests/test_execution_integration.py::test_tool_invocation_path_end_to_end`.
- **Provider Invocation:** the equivalent flow against a test-only
  `EchoProvider` implementing `BaseProvider` (no production provider was
  added — `providers` remains interfaces-only, unchanged from Sprint 5).
  See `examples/execution_provider_invocation.py` and
  `tests/test_execution_integration.py::test_provider_invocation_path_end_to_end`.

Both flows are also exercised together from one `ExecutionEngine` instance
built off one bootstrapped runtime
(`test_engine_dispatches_both_paths_from_the_same_runtime`), and both
failure modes — an unregistered tool id, an unregistered provider name —
are confirmed to return a failed `ExecutionResult` rather than raise
(`test_unregistered_*_operation_fails_cleanly_end_to_end`).

**Result: Execution Core is usable end-to-end exactly as designed, with no
architectural change required to prove it.**

## 2. Small internal improvements made this sprint

Two gaps surfaced only by actually wiring the bootstrap output into
Execution Core rather than constructing everything by hand (as the
Sprint 6 unit tests did):

1. **`RuntimeContext` had no way to produce an `ExecutionContext`.**
   `ExecutionContext.runtime` requires a real `core.runtime.Kernel`, and
   `RuntimeContext` deliberately never exposes its wrapped `Kernel` (by
   design, since Sprint 5 — see `docs/specs/bootstrap.md`). This is the
   identical problem `RuntimeContext.tool_context()` already solved for
   `ToolContext` in Sprint 5. Fixed the same way: added
   `RuntimeContext.execution_context()`, a factory method using the
   private `Kernel` reference internally without exposing it. Purely
   additive — no existing symbol changed, no public API broken. See
   `docs/specs/bootstrap.md` ("The same gap, again").
2. **`core.runtime.Kernel`'s own logger was double-namespaced.**
   `Kernel.__init__` built its logger via `get_logger(__name__)`, but
   `__name__` inside `core/runtime.py` is already
   `"mellivor_kernel.core.runtime"`, and `get_logger` prepends the
   `"mellivor_kernel."` root prefix again — every kernel-lifecycle log line
   was actually emitted under
   `"mellivor_kernel.mellivor_kernel.core.runtime"`, not
   `"mellivor_kernel.core.runtime"` as every other call site's convention
   would suggest. This went unnoticed in Sprint 2–6 because no prior test
   or example printed the log output for a human to read; running the two
   examples in this sprint surfaced it immediately. Fixed to
   `get_logger("runtime")`, matching the bare-name convention every other
   call site already uses. No test asserted the old (wrong) name, so
   nothing else needed to change.

Neither change touches a documented public contract per ADR-0004: (1) adds
a new method, and (2) corrects a private logger's internal name that was
never part of any subsystem's `__all__`.

## 3. Known weaknesses (documented, not fixed — out of this sprint's scope)

- **Execution Core cannot successfully dispatch a tool that declares
  required permissions.** `Dispatcher._dispatch_to_tool` calls
  `ToolExecutionPipeline.run(tool, tool_context, request.payload)` with no
  `granted_permissions` argument, so it always runs with the pipeline's
  default of `frozenset()` granted. Confirmed directly: dispatching
  `tools.builtin.HealthCheckTool` (which requires `KERNEL_INTERNAL`)
  through `ExecutionEngine` fails every time at the `permission_check`
  stage, while permission-free tools (`echo`, `version`) succeed. This is
  not a defect relative to this sprint's scope — Sprint 7 explicitly
  excludes Authorization, and `ExecutionRequest`/`Dispatcher` have no field
  to carry granted permissions through by design — but it means **no
  permissioned tool can be driven end-to-end via Execution Core until a
  future Authorization subsystem decides how permissions are granted and
  Execution Core is extended (deliberately, per ADR-0006) to carry them.**
  Anyone building on Execution Core today should know this before assuming
  it's a complete replacement for calling `ToolExecutionPipeline` directly.
- **`Dispatcher` requires both a `ToolRegistry` and a `ProviderRegistry` at
  construction**, even for a caller that only ever dispatches to one
  target (for example the provider-only example in this sprint still had
  to pass `runtime.tool_registry`, which happened to be empty). Minor
  ergonomic friction, not a defect — both registries already exist for
  free on any bootstrapped `RuntimeContext`, so no caller has actually had
  to construct one just for this.
- **`ExecutionEngine.execute()` performs no validation beyond what
  `ExecutionRequest`'s own constructor already enforces** (see
  `docs/specs/execution.md`). This was a deliberate Sprint 6 design choice,
  restated here because Integration Gate #1 is exactly the point at which
  that choice would have been revisited if real usage had shown it
  insufficient — it did not.

## 4. Conclusion

Execution Core proves usable against a real, bootstrapped runtime for both
named targets, without any change to its own public contract
(`ExecutionRequest`, `ExecutionContext`, `ExecutionResult`, `Dispatcher`,
`ExecutionEngine` are all byte-for-byte unchanged from Sprint 6). The one
new API surface added is `RuntimeContext.execution_context()` in
`bootstrap` — additive, not a change to anything Sprint 6 shipped. Per the
roadmap, Sprint 8 can proceed with new infrastructure (the event bus) on
top of a validated Execution Core.
