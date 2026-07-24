# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

Status as of Sprint 20: Sprints 1–5 shipped `core`, `config`, `providers`
(interfaces only, no concrete implementation), `tools`, and `bootstrap`.
Sprint 6 shipped `execution` (Execution Core) — see
[ADR-0006](../adr/0006-execution-core-orchestration-layer.md). Sprint 7 was
**Integration Gate #1**, an unscheduled validation sprint (per
[CLAUDE.md](../../CLAUDE.md) §14) that proved Execution Core end-to-end and
documented a real gap: no permissioned tool could be driven through
`ExecutionEngine` — see
[`docs/reviews/sprint7-execution-core-integration-gate.md`](../reviews/sprint7-execution-core-integration-gate.md).
Sprint 8 shipped `authorization` (`AuthorizationEngine`, `PermissionResolver`,
`PermissionSet`, `AuthorizationRequest`, `AuthorizationResult`) and closed
that gap by wiring an optional authorizer into `ExecutionEngine` — see
[ADR-0007](../adr/0007-authorization-engine-and-execution-decoupling.md) —
again ahead of the event bus originally recommended for that slot. Sprint 9
shipped that event bus (`Event`, `EventBus`, `InMemoryEventBus`,
`EventHandler`, `EventRegistration`) and wired both `ExecutionEngine` and
`AuthorizationEngine` to publish lifecycle events through it — see
[ADR-0008](../adr/0008-event-bus-and-lifecycle-events.md). Sprint 10
shipped the first concrete provider, `providers.claude.ClaudeProvider`
(Anthropic Messages API) — re-sequenced ahead of the memory abstraction
originally recommended for this slot, validating `BaseProvider`/
`execution`/`authorization` against a real LLM with no change to any of
the three; no ADR was needed there. Sprint 11 shipped that memory
abstraction (`Memory`, `MemoryStore`, `MemoryEntry`, `MemoryQuery`,
`MemoryResult`, `InMemoryStore`) — text memory only, no embeddings/vector/
RAG — and wired `ExecutionEngine` to optionally record execution outcomes
through it, with no dependency in either direction on any provider — see
[ADR-0009](../adr/0009-memory-subsystem-and-execution-recording.md). Sprint
12 shipped the workflow engine (`Workflow`, `WorkflowDefinition`,
`WorkflowStep`, `WorkflowContext`, `WorkflowEngine`, `WorkflowResult`) —
re-sequenced ahead of both plugin loading and agent lifecycle originally
recommended for slots 12–13, composing sequential `ExecutionEngine` calls
with no dependency back from `execution`/`authorization`/`memory`/`events`
— see
[ADR-0010](../adr/0010-workflow-engine-and-orchestration-boundary.md).
Sprint 13A shipped a first, deliberately minimal slice of `agents` — Agent
Runtime Core (`Agent`, `AgentDefinition`, `AgentContext`, `AgentEngine`,
`AgentResult`): an agent invokes exactly one workflow by delegating
entirely to `WorkflowEngine`, completing the chain
Agent → Workflow → Execution → Tool/Provider. No planning, reasoning,
reflection, or multi-agent composition yet — see
[ADR-0011](../adr/0011-agent-runtime-core-and-orchestration-chain.md).
Sprint 14 was **Integration Gate #2**, an unscheduled validation sprint (per
[CLAUDE.md](../../CLAUDE.md) §14) that audited the `v0.13.0` release
candidate end-to-end — package boundaries, dependency direction, public
exports, bootstrap composition, documentation, and dead code — and found no
defect requiring a code or architecture change; see
[`docs/release/release-audit.md`](../release/release-audit.md). The audit's
own "Release Risks" section named Security primitives and Observability as
the two largest remaining gaps toward `1.0.0`, which Sprints 15 and 16
addressed. Sprint 15 shipped a dedicated **Security Foundation**
(`security`) — `Secret`, `SecretProvider`, `SecretProviderRegistry`,
`SecurityPolicy`, `SecurityDecision`, `SecureConfiguration`, `AuditRecord`,
`AuditSink`, and the subsystem's exceptions — a contracts-and-primitives-only
package, deliberately not implementing authentication, OAuth, SSO, RBAC, or
any concrete secret backend, and structurally separate from `execution`,
`workflow`, `agents`, and `providers` — see
[ADR-0012](../adr/0012-security-foundation.md). It depends only on `core`
(for the shared `KernelError` base) and is not yet consumed by any other
subsystem. Sprint 16 shipped a dedicated **Observability Foundation**
(`observability`) — `ObservationContext`, `MetricsRecorder`,
`TraceRecorder`/`TraceSpan`, `StructuredEventSink`/
`StructuredObservationEvent`, no-op default implementations, and the
`Observability` dependency-injection wrapper — again contracts-and-no-op-only,
not a telemetry platform, with no exporter, backend, or vendor integration —
see [ADR-0013](../adr/0013-observability-foundation.md). Unlike `security`,
it has no dependency on any other kernel package, including `core`. Neither
foundation is wired into `execution`, `authorization`, `workflow`, `agents`,
or `bootstrap` yet; both remain available for a future sprint to consume
once a concrete use case dogfoods them, per [CLAUDE.md](../../CLAUDE.md) §13.
Sprint 17 wired the Sprint 15/16 foundations into their first real
consumers, closing the exact gap the "beyond Sprint 16" backlog named:
`authorization` records every grant/deny decision as a
`security.AuditRecord` through an injected `security.AuditSink`, and
`execution` emits a `StructuredObservationEvent` to an injected
`observability.StructuredEventSink` at the same three lifecycle points
`events.EventBus` already publishes to — both optional and independent
of the existing `EventBus` mechanism, with no change to either
subsystem's behavior when left unconfigured. No ADR was needed: this
sprint consumed the exact Protocol contracts ADR-0012/ADR-0013 already
defined, without changing them — the same reasoning Sprint 10 recorded.
See [`docs/specs/execution.md`](../specs/execution.md) and
[`docs/specs/authorization.md`](../specs/authorization.md). Sprint 18
finally delivered **Plugin loading** — deferred for three consecutive
sprint slots (12, 13A, and again after Sprint 14's gate) — shipping the
**Plugin Runtime Foundation** (`plugins`): `Plugin`, `PluginMetadata`,
`PluginContext`, `PluginCapability`, an immutable `PluginManifest`,
`PluginRegistry`, `PluginLoader`, and `PluginLifecycle` state
management — the contracts, manifest model, registry, loader, and
lifecycle a plugin is loaded, validated, registered, and run through. No
built-in plugins and no filesystem/entry-point discovery at this
sprint's scope; a caller supplies an explicit `PluginManifest` and
constructor directly. Depends only on `core` and the top-level `version`
module — see
[ADR-0014](../adr/0014-plugin-runtime-foundation.md). Sprint 19 shipped
the **Plugin SDK Foundation** (`plugin_sdk`) — `PluginBuilder`,
`BasePlugin`, `create_capability`/`create_manifest`/`create_metadata`,
`is_valid_capability`/`is_valid_manifest`/`is_valid_metadata` — a
developer-convenience layer over `plugins` adding no new contract or
validation rule of its own; every helper delegates to the corresponding
`plugins` constructor, so a change to a runtime validation rule needs no
SDK change. Depends only on `plugins` — see
[ADR-0015](../adr/0015-plugin-sdk-foundation.md). Sprint 20 shipped the
kernel's first built-in plugin, `SystemInfoPlugin`, in a new package,
`plugins_builtin` — exposing read-only kernel version, build info,
available capabilities, registered providers/tools, and runtime health,
built the way a third-party plugin author would build one and exercised
through the complete Loader → Registry → Lifecycle path against a real
`Kernel`, proving both Sprint 18 and 19 end to end per
[CLAUDE.md](../../CLAUDE.md) §13. No automatic registration or
discovery; `plugins_builtin` depends on `plugin_sdk`, `plugins`,
`providers`, `tools`, `core`, and `version` — the same latitude
`tools.builtin` already has — see
[ADR-0016](../adr/0016-system-info-built-in-plugin.md).
What follows is the approved recommendation for the remaining sprints.

Recommendation, not a decision — architecture and sprint sequencing remain
the user's to set. Based on the dependency shape already visible in
ADR-0002's responsibility list: lower-dependency, higher-reuse subsystems
first, `agents`/`workflow` last since they're consumers of everything else.

| Sprint | Subsystem | Why this position |
|---|---|---|
| 6 | ~~Event bus (`events`)~~ → **Execution Core** (`execution`), shipped | Re-sequenced ahead of the event bus: `execution` implements ADR-0002's named-but-unplaced "AI orchestration" responsibility and gives `tools`/`providers` a shared dispatch entry point sooner, which later sprints (`agents`, `workflow`) can build on directly. |
| 7 | **Integration Gate #1** — Execution Core validation, shipped | Inserted ahead of the event bus per CLAUDE.md §14: a newly implemented subsystem is validated end-to-end before more infrastructure is layered on top of it. Surfaced a real, if narrow, limitation — see the review's §3 — that Sprint 8 (Authorization) closed. |
| 8 | ~~Event bus (`events`)~~ → **Authorization Engine** (`authorization`), shipped | Re-sequenced again, ahead of the event bus: closes the exact gap Integration Gate #1 documented, and places ADR-0002's named-but-unplaced "Security primitives" responsibility (partially — permission-based authorization only) before `agents`/`workflow` need to call anything permission-checked. |
| 9 | **Event bus** (`events`), shipped | No dependencies beyond `core`; every later subsystem plausibly wants to publish/subscribe to lifecycle and state events — `execution` and `authorization` both do so immediately. Also the natural backbone for future tracing/audit work. |
| 10 | ~~Memory abstraction (`memory`)~~ → **First concrete provider** (`providers.claude.ClaudeProvider`), shipped | Re-sequenced ahead of memory: validates `BaseProvider` against a real LLM (Anthropic) while the contract is still cheap to change if it had needed to be — before `agents`/`memory` are built assuming a shape that turned out wrong. It didn't need to change. |
| 11 | **Memory abstraction** (`memory`), shipped | No dependencies beyond `core`; needed by `agents` for state/context persistence, and now proven usable by `execution` for recording outcomes without any provider dependency in either direction. |
| 12 | ~~Plugin loading (`plugins`)~~ → **Workflow engine** (`workflow`), shipped | Re-sequenced ahead of plugin loading and agent lifecycle: composes `execution`/`memory`/`events` (all already shipped) into sequential multi-step runs, proving the orchestration/execution boundary (ADR-0010) before `agents` is built on top of either. |
| 13A | ~~Plugin loading (`plugins`)~~ → **Agent Runtime Core** (`agents`), shipped | Re-sequenced ahead of plugin loading again: a minimal, single-workflow agent runtime completes the orchestration chain (ADR-0011) while `workflow` is still fresh, before plugin loading (an unrelated, lower-priority capability) or richer agent behavior (planning, multi-agent) are attempted. |
| 14 | **Integration Gate #2** — `v0.13.0` release-candidate audit, shipped | Inserted per CLAUDE.md §14, the same rationale as Sprint 7's gate: validate the release candidate spanning Sprints 1–13A end-to-end before more infrastructure is layered on top of it. Found no defect; named Security primitives and Observability as the two highest-priority remaining gaps, which Sprints 15–16 addressed. |
| 15 | ~~Plugin loading (`plugins`)~~ → **Security Foundation** (`security`), shipped | Re-sequenced ahead of plugin loading: places ADR-0002's named-but-only-partially-placed "Security primitives" responsibility with a reusable, business-agnostic contract surface (secrets, policy, audit) a future product or subsystem can build on, per Integration Gate #2's top risk finding. Foundation-only — no concrete secret backend, authentication, or RBAC — see ADR-0012. |
| 16 | ~~Plugin loading (`plugins`)~~ → **Observability Foundation** (`observability`), shipped | Re-sequenced ahead of plugin loading again: places ADR-0002's named-but-unplaced "Observability" responsibility beyond the structured logging shipped in Sprint 2, per Integration Gate #2's second-highest risk finding. Foundation-only — no metrics/tracing backend or vendor integration — see ADR-0013. |
| 17 | **Foundation adoption** — `security`/`observability` wired into `authorization`/`execution`, shipped | Directly closes the "beyond Sprint 16" backlog's top item: dogfooding the Sprint 15/16 foundations into an existing subsystem before either is considered proven, per CLAUDE.md §13. No new dependency direction — both wirings use the Protocol contracts already defined. |
| 18 | ~~Plugin loading (`plugins`)~~ → **Plugin Runtime Foundation** (`plugins`), shipped | Finally delivered after three consecutive deferrals (Sprints 12, 13A, and again after Sprint 14): the last fully-unimplemented ADR-0002 responsibility. Foundation-only, deliberately separated from discovery (a meaningfully larger, separate concern per ADR-0014). |
| 19 | **Plugin SDK Foundation** (`plugin_sdk`), shipped | Immediate follow-on to Sprint 18: the runtime contract was correct but unopinionated, the same gap `bootstrap.BootstrapBuilder` and `tools.builtin` each closed for their own layers. |
| 20 | **First built-in plugin** (`plugins_builtin.SystemInfoPlugin`), shipped | Proves Sprints 18–19 end to end against a real plugin, mirroring how `tools.builtin`'s three demonstration tools proved the Tool Runtime — required before either foundation's contract shape can be considered settled. |

**Beyond sprint 20 (not scheduled):** the remainder of **Plugin loading**
beyond Sprints 18–20 (filesystem/entry-point discovery, a plugin
marketplace, sandboxing, and additional built-in plugins beyond
`SystemInfoPlugin` — all explicitly deferred per ADR-0014/ADR-0016),
richer agent capabilities (planning, reasoning, reflection, multi-agent
composition, dynamic workflow selection — all deliberately deferred past
Sprint 13A), additional concrete providers (OpenAI, Gemini, Ollama —
explicitly out of scope for Sprint 10), a provider-side memory-consumption
mechanism (a provider reading prior memory as conversation context),
dynamic workflow steps (a step's request built from an earlier step's
result — deliberately not built in Sprint 12), parallel/scheduled workflow
execution, embeddings/vector search/RAG for `memory`, the remainder of
**Security primitives** beyond the Sprint 15 foundation and Sprint 17's
`AuditSink` wiring (a concrete `SecretProvider` backend, authentication,
OAuth, SSO, RBAC, encryption), and the remainder of **Observability**
beyond the Sprint 16 foundation and Sprint 17's `StructuredEventSink`
wiring (a concrete metrics/tracing backend or vendor integration, and a
trace/audit consumer built on top of `events`) — all still open per
ADR-0002, with no placement decided beyond what Sprints 15–20 already
placed.
