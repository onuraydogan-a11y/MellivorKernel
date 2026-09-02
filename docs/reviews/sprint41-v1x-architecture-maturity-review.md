# Sprint 41: v1.x architecture maturity and remaining roadmap review

Status: Architecture and roadmap review complete — v1.x architecture mature

Date: 2026-09-02

## Decision

**A — V1.X ARCHITECTURE MATURE: ENTER MAINTENANCE / EVIDENCE-DRIVEN
EVOLUTION.**

Mellivor Kernel v1.x has reached architectural maturity for its defined role:
a headless, provider-agnostic AI execution and lightweight orchestration
kernel. Every ADR-0002 responsibility has a stable boundary; all work approved
for v1.1 shipped additively; v1.2 proved caller-managed local inference through
the unchanged provider contract; packaging, documentation, tests, and the
Python 3.12/3.13 matrix are deterministic; and post-v1.2 research has either
remained isolated experimentally or received an explicit evidence/ownership
decision.

Maturity does not mean feature completeness for every AI product. It means the
stable substrate is sufficient, no approved Kernel work remains open, and new
capability must now be justified by real consumer evidence. No v2.0 process is
opened. No breaking requirement is known.

## Scope and evidence

The review audited all source packages, public exports, tests, specifications,
ADRs 0001–0027, release audits and notes for v1.0–v1.2, the roadmap, Sprints
34–40, CI/package metadata, debt markers, documented limitations, and sibling
consumer evidence already recorded by the recent Architecture Challenges.

The baseline is release `v1.2.0`, 1,015 tests, an empty mandatory dependency
set, isolated optional provider/experimental HTTP dependencies, and green CI on
Python 3.12 and 3.13. Post-v1.2 embeddings/vector work is not part of the
stable release contract.

## Capability inventory

Classification:

- **A** — stable and sufficient for the declared scope;
- **B** — stable, with concrete evidence-backed additive work remaining;
- **C** — experimental/internal;
- **D** — deferred pending consumer evidence;
- **E** — product/deployment responsibility; and
- **F** — concrete technical debt or hardening required.

| Capability | Class | Assessment |
|---|---:|---|
| Core/runtime and dependency injection | A | Stable runtime, contracts, errors, logging, and explicit service composition; no demonstrated gap |
| ExecutionEngine | A | Authoritative synchronous execution lifecycle with optional authorization, events, memory, and observations |
| Dispatcher | A | Stable routing to tool/provider registries; no second execution path is required |
| Authorization seams | A | Structural `Authorizer` boundary and permission enforcement before dispatch are sufficient for Kernel authorization |
| Identity, authentication, OAuth/OIDC/SSO | E | Product/platform identity concerns; not Kernel authorization primitives |
| Providers | A | `BaseProvider` proven by Claude, OpenAI, Gemini, and Local adapters; optional dependencies remain isolated |
| Workflows | A | Static, dynamic-request, bounded/configurable parallel, and eligibility-guard execution are additive over frozen v1.0 contracts |
| Tools | A | Contract, registry, permission declarations, pipeline, results, and built-in proofs are sufficient |
| Plugin runtime/SDK/discovery | A | Explicit trusted-code loading, validation, lifecycle, registry, filesystem and entry-point discovery are sufficient |
| Plugin marketplace/distribution | E | Packaging, catalog, commerce, remote installation, and trust operations belong outside Kernel |
| Agents | A for baseline; D for richer behavior | One agent delegates to one workflow; planning/reasoning/autonomy remain deferred |
| Memory | A | `MemoryStore` proven by process-local and durable SQLite implementations |
| Secrets/security foundation | A | Secret/audit/policy seams plus `EnvSecretProvider` are sufficient; product identity and storage policy remain external |
| Events | A for in-process; E for distributed | Deterministic synchronous lifecycle notification is stable; brokers/outboxes/workers are deployment concerns |
| Observability | A for neutral seams; E for adapters | Standard logging, correlation, metrics/tracing Protocols, and structured observations exist; vendor lifecycle stays external |
| Configuration/bootstrap/AIEngine | A | Explicit environment/settings/runtime composition and the supported orchestration composition root are stable |
| Embedding contracts/adapter | C | Internal ADR-0027 proof, excluded from stable exports and v1.x promises |
| Vector contracts/InMemoryVectorStore | C | Internal non-production proof; no external backend or consumer workload |
| RAG/retrieval policy | D/E | No consumer evidence; ingestion, ranking, completion policy, and product retrieval behavior are outside the current Kernel |

No subsystem is classified B or F at completion of this review. There is no
approved additive Kernel feature waiting to ship and no concrete defect that
blocks maintenance mode. Documented operating limits and unproven research are
not silently relabeled as debt.

## Release evolution

### v1.0.0 — stable substrate

v1.0 froze the complete initial public surface under ADR-0005, ADR-0019, and
ADR-0020:

- core runtime, configuration, bootstrap, tools, dispatcher, execution, and
  permission-based authorization;
- Claude and OpenAI implementations of `BaseProvider`;
- synchronous in-process events, text memory, sequential workflows, and the
  baseline agent lifecycle;
- security/audit and observability “bring your own backend” foundations;
- plugin runtime, SDK, built-in proof, filesystem/entry-point discovery; and
- `AIEngine` composition of the runtime chain.

The release made the SemVer/deprecation promise binding. It intentionally did
not include persistent memory, evolved workflow options, more providers, a
concrete secret source, richer agents, vector/RAG, distributed delivery,
marketplaces, telemetry vendors, or identity services.

Compatibility model: documented package exports and public contract behavior
are frozen; removal/breakage requires a major release, while additive types and
optional keyword behavior may ship in a minor release.

### v1.1.0 — additive contract proof and workflow evolution

v1.1 completed every item that ADR-0019 had explicitly deferred to it:

- `SQLiteMemoryStore` became the second, persistent `MemoryStore` proof
  (ADR-0021);
- `EnvSecretProvider` became the first concrete secret source (ADR-0022);
- `GeminiProvider` became the third provider implementation (ADR-0023); and
- `WorkflowExecutionOptions` added dynamic request resolution, opt-in parallel
  groups, and `not_before` guards while ADR-0025 restored the exact v1.0
  `WorkflowStep` contract after rejecting ADR-0024's breaking shape.

All 157 v1.0 exports remained available. Additions were new types, optional
modules, and optional keyword parameters. The release also corrected provider
dependency bounds and an accidental transitive HTTPX test dependency.

Limitations remain explicit: scheduling is eligibility, not a durable service;
a SQLite connection is not shared across parallel branches without caller
synchronization; provider-specific advanced modalities remain adapter scope.

### v1.2.0 — local endpoint interoperability

v1.2 added only `LocalProvider` (ADR-0026), using direct HTTPX against a
caller-managed OpenAI-compatible endpoint. It preserved every v1.1 contract
and kept HTTPX in the optional `local` extra. Import and construction have no
network behavior; Kernel does not install models, start runtimes, manage
processes, or fall back to cloud services.

The validated promise is the documented protocol subset, not certification of
every Ollama, LM Studio, vLLM, or model build. This is an additive provider
proof, not model-runtime management.

### Post-v1.2 work

Sprints 34–36 produced an accepted architecture and internal proof for
embedding/vector contracts. The proof adds an internal HTTPX embedding adapter
and non-production in-memory vector store, but no stable export, RAG behavior,
external backend, persistence, product retrieval policy, or release promise.

Sprints 37–40 selected no additional Kernel implementation:

- external vector storage is deferred until a consumer presents a real
  workload; pgvector is only the first candidate to reassess;
- planning/reasoning/autonomous loops are deferred;
- distributed messaging is product/deployment responsibility; and
- telemetry/vendor adapters are product/deployment responsibility using the
  existing neutral seams.

## Remaining Future Research reconciliation

| Item | Current decision and owner | Evidence required to reopen | v1.x candidate? | Possible major trigger? |
|---|---|---|---:|---:|
| Embeddings | Internal Kernel experiment | Approved workload, dogfood, security proof, stable naming review | Yes, additively after gates | Only if stable provider contracts must break; not currently |
| External vector store | Deferred; optional Kernel adapter only if justified | Concrete consumer scale/topology/owner plus second materially different backend | Yes, optional/internal first | Only if the proven store contract is inadequate in a non-additive way |
| RAG | Product/shared-library policy | Repeated cross-product retrieval pipeline with identical infrastructure need | Usually no | No by itself |
| Agent planning | Deferred; shared library/product first | Concrete consumer unable to generate existing workflows externally | Possibly, with ADR | Only if authoritative workflow/execution contracts must change |
| Reasoning/reflection | Product/shared library | Observable structured feedback need; never chain-of-thought exposure | Usually no | No by itself |
| Autonomous loops | Product | Approved bounded goal loop, safety limits, cancellation, costs, and human gates | No current candidate | Only if a reusable runtime requirement cannot compose existing execution |
| Multi-agent coordination | Separate Future Research | Two or more real products with common coordination semantics | Unknown | Possible, only with unavoidable contract breakage |
| Distributed events/brokers | Product/deployment | Cross-product need to distribute Kernel lifecycle events, not business messages | No current candidate | Only if existing EventBus must change rather than remain in-process |
| Plugin marketplace | Product/commercial platform | Concrete catalog/distribution owner and repeated consumer need | No | No; marketplace can remain external |
| Plugin signing/sandbox/remote install | Product/deployment or separate trusted distribution library | Threat model, packaging format, trust roots, lifecycle and deployment evidence | Not currently | Possible only if in-process plugin contract must be replaced |
| Telemetry/vendor integration | Product/deployment | Duplicated safe adapter logic across consumers and explicit lifecycle evidence | Optional adapter could be additive | Only if frozen observability Protocols require incompatible replacement |
| Authentication/login/sessions | Product/identity platform | No reopening for ordinary product identity needs | No | No |
| OAuth/OIDC/SSO | Product/platform infrastructure | Only a cross-product, transport-neutral runtime seam missing from Kernel | No current candidate | No by itself |
| RBAC/tenant membership | Product | Evidence that generic permissions cannot express a Kernel operation gate | No current candidate | Possible only if authorization contracts require mandatory identity fields |
| Encryption at rest | Backend/product/deployment | Concrete backend data-classification requirement | Adapter-specific | No by itself |
| Provider memory consumption | Product/shared library | Repeated model-context assembly need independent of product policy | Possibly additive | Only if `BaseProvider` request shape must break |

Deferred items remain deferred. Product/deployment assignments remain outside
Kernel. No prior decision is reopened by this inventory.

## Authentication, OAuth, SSO, and RBAC boundary

### What Kernel already provides

`ExecutionEngine` consults an optional structural `Authorizer` before
dispatch. `AuthorizationEngine` resolves the permissions declared by a tool,
compares them with explicitly supplied permission strings, denies before tool
invocation, publishes lifecycle events, and optionally records audit entries.
`PermissionSet`, `AuthorizationRequest`, and `AuthorizationResult` are
immutable. `ToolExecutionPipeline` independently enforces permissions during
tool execution. A selected tool never grants itself authority.

`ExecutionContext` and `ToolContext` deliberately carry Kernel runtime state,
not business identity. `SecurityPolicy` is a generic subject/action seam, but
Kernel does not define a user, tenant, role, token, or session.

This is sufficient for Kernel: it receives an already-authenticated caller's
effective permissions and enforces them at its operation boundary.

### Ownership decision

Products or platform identity infrastructure own:

- login, users/service accounts, password policy, enrollment and recovery;
- browser/API sessions, cookies, CSRF, token issuance and refresh;
- OAuth 2.0, OpenID Connect, SSO, federation, JWKS and token validation;
- tenant membership, organizations, role assignment and role hierarchy;
- RBAC/ABAC policy authoring, administration, caching and lifecycle;
- mapping a validated principal/role/claim set into Kernel permissions; and
- identity audit, retention, revocation and UI.

Kernel must not validate an identity token or infer tenant authority from
request metadata. The product must authenticate first, resolve policy, pass
only the effective permission set, and retain tenant isolation in its data and
service boundaries.

No additional identity primitive is approved. Adding `principal`, `tenant`,
or `roles` to frozen execution contexts would couple Kernel to product policy
and is unnecessary for current authorization.

## Plugin marketplace and distribution boundary

Kernel already owns the reusable plugin mechanics: `Plugin` and manifest
contracts, validation, lifecycle, registry, explicit loader, SDK helpers,
filesystem discovery, Python entry-point discovery, version compatibility,
and a built-in plugin proving the path.

Discovered plugin code runs with the same trust and process authority as other
Python code. Kernel does not claim sandboxing or remote trust.

The following remain outside Kernel:

- package hosting, catalog search, ratings, billing, licensing and commerce;
- remote download/installation/update/removal and dependency resolution;
- organization allowlists and administrator policy;
- signing authorities, certificate/key lifecycle, provenance attestations and
  malware review;
- deployment-specific sandbox/process/container isolation; and
- marketplace UI and product-specific capability presentation.

A distribution service may produce a locally installed, verified plugin that
the existing `PluginDiscovery` loads. Kernel must not become the marketplace,
package manager, trust authority, or deployment control plane. A separate
shared distribution library is preferable if repeated noncommercial mechanics
emerge.

## Technical debt and hardening audit

### Real findings

One current documentation inconsistency was found and corrected in this
sprint: README still described the already-tagged v1.2.0 release as a release
candidate awaiting Product Owner approval.

No source TODO/FIXME/HACK marker, deprecated Kernel API, skipped/xfail test,
mandatory dependency, accidental stable embedding/vector export, unresolved CI
failure, confirmed dead code, or duplicate execution abstraction was found.

The following are concrete constraints but not unowned debt:

- `InMemoryStore`, `SQLiteMemoryStore`, and experimental
  `InMemoryVectorStore` do not promise shared-instance thread safety; the
  limitation and caller alternatives are documented.
- workflow `max_concurrency=None` may submit every step in one explicitly
  requested parallel group; callers can set a positive bound. Kernel owns no
  hidden loop or executor.
- observability contexts/events accept free-form attributes, and execution
  failure observations include error text. Sprint 40 therefore requires
  consumer adapters to filter/redact before remote export. Changing frozen
  contracts without an evidence-backed replacement is not authorized.
- `MetricsRecorder` and `TraceRecorder` remain stable single-consumer/no-op
  abstractions without Kernel instrumentation. This was knowingly ratified at
  v1.0 and is a promotion/evidence risk, not a current defect.
- Gemini's SDK may override its configured timeout in some code paths; this is
  a documented upstream SDK constraint, not a Kernel contract defect.

These constraints belong in maintenance risk monitoring. None justifies an
implementation sprint absent a reproduced consumer failure or security issue.

### Speculative improvements excluded from backlog

Async APIs, streaming everywhere, richer provider payloads, universal thread
safety, distributed queues, a scheduler daemon, plugin hot reload/sandboxing,
new telemetry sinks, generalized identity models, automatic retries, model
downloads, RAG, autonomous agents, renamed contracts, and consolidated package
surfaces are not debt merely because they could be built.

## Stable public API maturity

### Strongly proven abstractions

- `BaseProvider`, configuration, capabilities, registry, and factory: four
  concrete providers across three vendor SDK shapes and direct HTTPX.
- `MemoryStore`: in-memory and persistent SQLite implementations.
- `SecretProvider`: structural fakes plus concrete environment implementation
  and registry fallback.
- workflow/execution composition: sequential, dynamic-request, parallel, and
  scheduled-eligibility modes with frozen v1.0 step/definition contracts.
- tools/plugins: built-ins and integration paths prove registration, loading,
  lifecycle, permission and invocation behavior.
- `StructuredEventSink` and `AuditSink`: Kernel call sites plus a real
  product-owned observability sink/audit consumption evidence.

### Single-implementation or intentionally minimal abstractions

`EventBus` has one in-process implementation; distributed semantics were
explicitly rejected as the same abstraction. `Dispatcher`, `ExecutionEngine`,
`WorkflowEngine`, and `AgentEngine` are authoritative engines, not backend
interfaces requiring multiple implementations. `MetricsRecorder`,
`TraceRecorder`, `SecurityPolicy`, and `SecureConfiguration` remain lightly or
externally consumed foundations.

No stable abstraction is known to be inadequate for its promised scope.
Single implementation alone does not prove over-generalization when the type
defines a deliberate injection/testing boundary or an authoritative runtime.

## Experimental promotion gates

Embedding/vector code may remain internal indefinitely. Research code does not
acquire a release deadline merely by existing.

Promotion requires all of the following:

1. a named Mellivor consumer with an approved embedding/vector workload;
2. documented scale, persistence, topology, isolation and operational owner;
3. dogfooding through a real consumer integration rather than contract-only
   tests;
4. a second, materially different external `VectorStore` backend selected from
   deployment evidence and implemented without changing the core contract;
5. real embedding endpoint/runtime interoperability evidence in addition to
   deterministic HTTP tests;
6. security validation for text/vector/metadata/credential/body redaction,
   tenant routing, deletion and cross-namespace isolation;
7. optional dependency, lifecycle, failure-translation and packaging proof;
8. API naming, module placement, export, documentation and SemVer review; and
9. an integration gate proving consumer portability across the two stores.

Failure of a gate means the types stay under `_embeddings`/`_vector`, outside
stable package exports. RAG is not an automatic promotion consequence.

## Objective v1.x maturity criteria

The v1.x architecture is mature when:

1. every declared Kernel responsibility has a documented stable boundary;
2. execution, authorization and dispatch have one authoritative path;
3. providers are proven across multiple materially different implementations;
4. memory has both process-local and persistent implementations;
5. a concrete secret source proves the secret contract;
6. workflow evolution occurs additively without modifying frozen definitions;
7. local inference connects through a caller-owned runtime boundary;
8. security, audit, observability, event and product-policy boundaries are
   explicit;
9. base packaging remains dependency-free and integrations remain optional;
10. tests, lint, formatting, strict typing, builds and supported-Python CI are
    deterministic;
11. ADRs/specs/release notes/roadmap match implementation and tags;
12. speculative work uses consumer-evidence gates and explicit ownership; and
13. experimental code is clearly isolated from stable exports and promises.

All thirteen criteria are currently satisfied. Future CI failures,
documentation drift, vulnerability disclosures, or reproducible contract
defects return to the maintenance backlog; they do not retroactively make the
architecture immature.

## Legitimate v2.0 triggers

A major line is justified only by approved, repeated consumer evidence that a
stable contract must break and additive evolution cannot express the need.

| Potential break | Evidence and why additive evolution is insufficient | Migration implication |
|---|---|---|
| `BaseProvider` request/result model | Multiple consumers require one unified streaming/tool/multimodal contract that cannot coexist as a sibling capability or additive method | Provider adapters and callers migrate request/result construction; compatibility adapter and deprecation plan required |
| Execution lifecycle/API | Real workloads require async cancellation, resumable/durable execution, or mandatory resource budgets that cannot wrap current synchronous execution | Engines, contexts, results and product composition migrate together |
| `Dispatcher`/`ExecutionTarget` | A reusable target class requires open-ended routing that the frozen enum/dispatcher cannot add safely | Target registration and exhaustive consumer logic require migration |
| Workflow contracts | Durable/resumable workflows require stable step identity, persisted state or graph semantics incompatible with `WorkflowStep`/`WorkflowDefinition` | Definitions need conversion tooling and dual-read guidance |
| `MemoryStore` | Multiple backends require transactions, pagination or consistency semantics that cannot be added as optional sibling Protocols | Store adapters and query/result consumers migrate |
| Authorization contract | Repeated consumers prove mandatory principal/tenant-aware authorization cannot be injected or mapped to current permissions | Products must adapt identity-to-permission mapping and execution calls |
| Plugin trust/lifecycle | Required out-of-process isolation makes the current in-process object lifecycle fundamentally unsafe or misleading | Plugin manifests, loading, IPC and lifecycle implementations migrate |
| Observability contract | Real adapters prove current metrics/tracing methods cannot represent required safe lifecycle and a sibling contract would create contradictory semantics | Instrumentation and adapters migrate with explicit SDK lifecycle |

Every trigger requires a Proposed architecture ADR, affected-consumer
inventory, compatibility test matrix, migration guide, deprecation analysis,
security review, and Product Owner approval before implementation. Prefer an
additive v1.x sibling contract whenever both models can coexist honestly.

### What does not justify v2.0

Sprint count, project age, marketing, a “clean slate,” experimental research,
another provider or optional backend, a product-specific feature, internal
refactoring, cleaner naming, dependency upgrades, documentation cleanup,
performance tuning, or an additive adapter do not justify a major release.

## Architectural endpoint and ESB comparison

The most accurate description is **headless AI execution and lightweight
orchestration kernel**.

Kernel supplies typed registration, dispatch, execution, authorization gates,
workflow composition, basic agent lifecycle, provider/tool/plugin integration,
memory, events, security and observability seams. “AI runtime bus” can describe
the central dispatch/composition role informally, but “Enterprise Service Bus”
would be misleading.

A classical ESB commonly owns network integration, protocol mediation,
message transformation, durable queues, routing across services, delivery
guarantees, broker operations and centralized enterprise integration policy.
Mellivor Kernel executes in a consuming process, uses direct typed calls, has a
synchronous in-process EventBus, owns no distributed transport, and does not
mediate arbitrary enterprise services. It is an integration kernel for AI
runtime components, not an enterprise message bus.

Permanent scope boundaries preventing ESB/platform creep are:

- UI and product APIs;
- users, tenants, roles, sessions and identity administration;
- OAuth/OIDC/SSO services and token lifecycle;
- business workflows, prompts, domain rules and approval policy;
- brokers, workers, outboxes, service discovery and distributed scheduling;
- plugin marketplace/catalog/commerce and remote package operations;
- deployment control planes, collectors, dashboards and alerting;
- model downloads, runtime/process/GPU operations and cloud fallback;
- RAG ingestion/chunking/reranking and product retrieval policy; and
- autonomous-agent and multi-agent product behavior without reusable evidence.

## Maintenance and evolution posture

No feature sprint is approved by this review. The v1.x line should now accept:

- security and dependency maintenance;
- reproducible bug fixes and compatibility corrections;
- documentation and packaging corrections;
- additional provider/backend adapters only when a real consumer needs them;
- additive evolution supported by an ADR where architecturally significant;
  and
- bounded internal research that remains isolated until its promotion gates
  pass.

The next release should be a patch only when a real maintenance change exists,
or a minor only when approved evidence-backed additive capability exists.
There is no reason to publish an empty release or open v2.0 now.
