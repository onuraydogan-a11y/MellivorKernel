# Roadmap

Moved from `RELEASE_NOTES_v0.5.0.md`'s "Sprint roadmap (6–10)" section
(Sprint 5 docs reorganization) into its own file, so it can be kept current
as a living document rather than frozen inside one release's notes.
`RELEASE_NOTES_v0.5.0.md` remains the historical record of what that
release actually shipped; this file is where roadmap content should be
updated going forward.

**A note on Sprints 21–23.** This file was not updated during those three
sprints, per each sprint's own explicit instruction at the time (their
scope was additive implementation, and touching the roadmap was
deliberately excluded to keep each sprint's diff scoped to its own
package). Sprint 24 backfills all three below, then adds itself.

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
[ADR-0016](../adr/0016-system-info-built-in-plugin.md). Sprint 21 shipped
the **Plugin Discovery Foundation** (`plugin_discovery`) — exactly one
class, `PluginDiscovery`, discovering plugins from a filesystem location
and loading/registering them through the existing, unmodified
`PluginLoader`/`PluginRegistry`, introducing no new loading, validation,
or registration logic of its own. Depends only on `plugins` and `core`;
no marketplace, remote plugins, sandboxing, hot reload, signature
verification, or package installation — see
[ADR-0017](../adr/0017-plugin-discovery-foundation.md). Sprint 22
shipped the **AI Engine Foundation** (`ai_engine`) — a pure composition
layer, `AIEngineBuilder`/`AIEngine`, assembling an already-bootstrapped
`RuntimeContext` and the orchestration-chain engines (`execution`/
`workflow`/`agents`, with `authorization` optionally consulted) plus a
`PluginRegistry`, closing the gap between "every capability ADR-0002
names exists" and "a product can adopt the kernel through one entry
point." Introduces no business logic, chat feature, prompting,
reasoning, planning, orchestration decision, or provider-selection logic
of its own; not a new ADR-0002 responsibility, since it composes
responsibilities that already exist — see
[ADR-0018](../adr/0018-ai-engine-foundation.md). Sprint 23 shipped the
kernel's second concrete provider, `providers.openai.OpenAIProvider`
(OpenAI Chat Completions API) — deliberately a structurally different
request shape than `ClaudeProvider`'s (a multi-turn message list, not a
flat prompt string), proving `BaseProvider`'s contract generalizes a
second time with no change to it. No ADR was needed, matching Sprint
10's own precedent for the first optional vendor dependency; see the
`OpenAIProvider` section of
[`docs/specs/providers.md`](../specs/providers.md). Sprint 24 was a
documentation-only **Release Readiness & Scope Lock**: every ADR-0002
responsibility was classified as `Included in v1.0`, `Deferred to v1.1`,
or `Future research`, closing the release checklist's previously-open
"the release decision is recorded in an ADR" gate item — see
[ADR-0019](../adr/0019-release-readiness-and-scope-lock.md) and the
updated [`docs/release/v1.0-release-checklist.md`](../release/v1.0-release-checklist.md).

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
| 21 | **Plugin Discovery Foundation** (`plugin_discovery`), shipped | Delivers the one piece of Plugin loading Sprints 18–20 deliberately deferred: real filesystem discovery, through the existing, unmodified `PluginLoader`/`PluginRegistry`. See ADR-0017. |
| 22 | **AI Engine Foundation** (`ai_engine`), shipped | Closes the composition gap between "every ADR-0002 capability exists" and "a product can adopt the kernel through one entry point" — ranked highest in a dedicated Architecture Challenge against a second built-in plugin and an additional provider. See ADR-0018. |
| 23 | **Additional Provider Foundation** (`providers.openai.OpenAIProvider`), shipped | Proves `BaseProvider` generalizes a second time, deliberately against a structurally different request shape than Claude's. No ADR needed, matching Sprint 10's own precedent. |
| 24 | **Release Readiness & Scope Lock**, shipped (documentation only) | Resolves the release checklist's own named prerequisite (ADR-0005: "a decision to be made explicitly via a future ADR") before any further capability sprint, since every remaining candidate's own checklist row required a decision before an implementation. See ADR-0019. |

**Beyond Sprint 24: classified, not scheduled.** As of Sprint 24
([ADR-0019](../adr/0019-release-readiness-and-scope-lock.md)), every
remaining item below has a stated classification — it is no longer an
undifferentiated backlog. See
[`docs/release/v1.0-release-checklist.md`](../release/v1.0-release-checklist.md)
for the responsibility-by-responsibility detail behind each entry.

**Deferred to v1.1** — real, scoped, schedulable directly once `1.0.0`
ships, with no further design gate needed first:

- Workflow: dynamic steps (a step's request built from an earlier step's
  result), parallel execution, scheduling.
- Memory: a second, persistent `MemoryStore` implementation (mirroring
  the `providers` precedent — a second concrete implementation proving
  the abstraction).
- Providers: additional concrete providers (Gemini, local models).
- Security: a concrete `SecretProvider` backend (the same proven
  pattern as a second provider).

**Future research** — open-ended, no committed design or timeline; some
of these raise a genuine, unresolved question of whether the capability
belongs in the kernel at all versus a consuming product, per
[ADR-0003](../adr/0003-repository-boundaries.md), and would need their
own Architecture Challenge before being scheduled:

- Agent lifecycle: planning, reasoning, reflection, multi-agent
  composition, dynamic workflow selection.
- Memory: a provider-side memory-consumption mechanism (a provider
  reading prior memory as conversation context), embeddings, vector
  search, RAG.
- Plugin loading: a marketplace, remote plugins, sandboxing, hot reload,
  signature verification, package installation.
- Event bus: distributed delivery (Kafka/NATS/Redis-backed).
- Observability: a concrete metrics/tracing backend or vendor
  integration, and a trace/audit consumer built on top of `events`.
- Security: authentication, OAuth, SSO, RBAC, encryption.

## v1.1: approved sprint sequence (2026-08-26)

Product Owner direction, superseding "classified, not scheduled" for the
`Deferred to v1.1` bucket above — these five sprints are now the approved
order, not a recommendation:

| Sprint | Item | Status |
|---|---|---|
| 27 | Persistent `MemoryStore` (`memory.SQLiteMemoryStore`) | Shipped — see [ADR-0021](../adr/0021-persistent-memory-sqlite-store.md) |
| 28 | Concrete `SecretProvider` backend (`security.EnvSecretProvider`) | Shipped — see [ADR-0022](../adr/0022-env-secret-provider.md) |
| 29 | Gemini provider (`providers.gemini.GeminiProvider`) | Shipped — see [ADR-0023](../adr/0023-gemini-provider.md) |
| 30 | Workflow evolution (dynamic steps / parallel / scheduling) | Shipped; v1.0 compatibility repaired — see [ADR-0025](../adr/0025-workflow-execution-options-compatibility-repair.md) |
| 31 | v1.1 Release Gate | Complete — `v1.1.0` released |

Sprint 31 repeated the complete release-readiness audit against the repaired
Sprint 30 architecture. The v1.0 public surface remains compatible, all local
and CI gates are green, packaging and isolated-install checks pass, and the
`1.1.0` release commit passed its final CI gate and the Product Owner approved
and published the tag. See
[`docs/release/v1.1-release-audit.md`](../release/v1.1-release-audit.md).

Sprint 27 shipped `memory.SQLiteMemoryStore`, a second, durable
`MemoryStore` implementation proving the existing abstraction beyond
`InMemoryStore` — a SQLite-backed store using only the Python standard
library, added with zero change to `MemoryStore`, `MemoryEntry`,
`MemoryQuery`, `MemoryResult`, `MemoryError`, `InMemoryStore`, or
`Memory`. See ADR-0021 and
[`docs/specs/memory.md`](../specs/memory.md).

Sprint 30 shipped additive workflow evolution through external
`WorkflowExecutionOptions`: callable-based dynamic request construction,
opt-in contiguous parallel groups with deterministic result presentation, and
an injectable-clock `not_before` eligibility guard. The original direct-field
design was rejected at the v1.1 release gate; ADR-0025 restores the exact v1.0
`WorkflowStep` dataclass contract. Existing static sequential behavior is
unchanged. Durable scheduling remains an external-runtime responsibility;
Kernel adds no daemon, queue, cron service, persistence, or background worker.
See ADR-0025 and
[`docs/specs/workflow.md`](../specs/workflow.md).

Sprint 28 shipped `security.EnvSecretProvider`, the first concrete
`SecretProvider` implementation — read-only, backed by process
environment variables, using only the Python standard library (`os`,
`re`), added with zero change to `SecretProvider`, `Secret`,
`SecretProviderRegistry`, `SecurityPolicy`, `SecureConfiguration`,
`SecurityDecision`, `AuditRecord`, `AuditSink`, `SecurityError`, or
`SecureConfigurationError`. Three new, backend-agnostic exceptions were
added (`SecretNotFoundError`, `SecretValueError`,
`SecretConfigurationError`), each a `SecurityError` subclass. See
ADR-0022 and [`docs/specs/security.md`](../specs/security.md).

Sprint 29 shipped `providers.gemini.GeminiProvider`, the kernel's third
concrete provider — backed by the Gemini Developer API via the
`google-genai` SDK (a new optional dependency, `pip install
mellivor-kernel[gemini]`), added with zero change to `BaseProvider`,
`ProviderCapabilities`, `ProviderConfiguration`, `ProviderHealthCheck`,
`ProviderRegistry`, `ProviderFactory`, or the shared `providers`
exceptions. Reuses `OpenAIProvider`'s request/response key names;
translates Gemini's `.code`-based error model and `httpx`
transport-level failures into the same five-class exception shape
(`GeminiProviderError`/`GeminiAuthenticationError`/`GeminiTimeoutError`/
`GeminiConnectionError`/`GeminiResponseError`) `ClaudeProvider`/
`OpenAIProvider` already established. See ADR-0023 and
[`docs/specs/providers.md`](../specs/providers.md).

## Post-v1.1 development

| Sprint | Item | Status |
|---|---|---|
| 32 | Local model provider (`providers.local.LocalProvider`) | Shipped and protocol-validated — see [ADR-0026](../adr/0026-local-provider-openai-compatible-endpoint.md) and the [Sprint 32 validation](../reviews/sprint32-local-provider-validation.md) |

Sprint 32 begins post-v1.1 development without defining a broader v1.2
roadmap. `LocalProvider` connects only to a caller-managed, already-running
OpenAI-compatible endpoint. It does not install runtimes, download models,
start processes, or expand `BaseProvider`. Ollama-native lifecycle/model
management, streaming, tools, multimodal input, and embeddings remain outside
this sprint.
