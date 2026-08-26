# Mellivor Kernel

Mellivor Kernel is the **AI Enterprise Kernel** underpinning Mellivor One and
future Mellivor enterprise products. It is not an application, and it is not
a product. It is the substrate that enterprise AI applications are built on
top of.

## Vision

Every AI-powered product Mellivor ships needs the same underlying
capabilities: agent lifecycle, a workflow engine, memory, tool execution, an
event bus, plugin loading, and a way to talk to one or more model providers —
plus configuration, observability, and security primitives to run all of it
safely in an enterprise setting. Historically these capabilities get rebuilt,
slightly differently, inside every product. That duplication is the problem
this repository exists to solve.

Mellivor Kernel provides those capabilities once, as a set of stable,
well-documented contracts with pluggable implementations, so that:

- **Mellivor One** and every future enterprise product consume the kernel
  instead of reinventing it.
- Product teams can innovate on business logic without touching core AI
  plumbing.
- Model providers and other infrastructure choices are swappable behind the
  kernel's provider abstraction instead of hard-wired into product code.
- Agent, workflow, memory, and tool-execution primitives are consistent,
  testable, and independently versioned.

See [ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md)
for the full scope decision behind this vision.

## What this repository is

- An **AI Enterprise Kernel**: core contracts, agent/workflow primitives, and
  reference implementations that other Mellivor products depend on.
- **Business-agnostic**: it must never contain CRM, Legal, HR, Finance,
  Security, or any other business/domain logic. That logic always lives in
  external, consuming applications.
- **Provider-agnostic**: model providers are integrated through the
  `providers` subsystem, never assumed by core code.

## What this repository is not

- Not a software development framework — it exists to power enterprise AI
  applications, not to be generically useful.
- Not a CRM, Legal, HR, Finance, Security, or any other business application.
- Not a UI.
- Not a home for business modules or product-specific logic.
- Not a complete implementation of the richest possible version of every
  responsibility in [ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md)
  — several ship a stable baseline with richer capability deferred by
  design; see [Status](#status) below for exactly what `1.0.0` covers and
  what's deferred.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the high-level design:
the kernel's subsystems and how they relate.

- [`docs/architecture/principles.md`](docs/architecture/principles.md) —
  the kernel's guiding principles.
- [`docs/architecture/roadmap.md`](docs/architecture/roadmap.md) — the
  current sprint roadmap.

Architecturally significant decisions are recorded as ADRs in
[`docs/adr/`](docs/adr/README.md).

Detailed specifications for individual subsystems live in
[`docs/specs/`](docs/specs/README.md) as they are written.

## Repository layout

```
src/mellivor_kernel/
    core/           Lifecycle, contracts, dependency boundaries
    agents/         Agent lifecycle
    workflow/        Workflow engine
    memory/          Memory abstraction
    tools/           Tool execution
    events/          Event bus
    plugins/         Plugin runtime foundation: contracts, manifest, registry, loader, lifecycle
    config/          Configuration
    providers/       Multi-LLM provider abstraction
    bootstrap/       Composition layer: assembles core/config/providers/tools
    execution/       Execution orchestration: request/context/result, dispatch, engine
    authorization/   Permission-based authorization for execution requests
    security/        Security foundation: secrets, policy, secure config, audit contracts
    observability/   Observability foundation: metrics/tracing/event contracts, no-ops
    plugin_sdk/      Plugin SDK: builder, base plugin, creation/validation helpers
    plugins_builtin/ Built-in plugins: SystemInfoPlugin
    plugin_discovery/ Plugin Discovery: filesystem manifest scanning, entry-point loading
    ai_engine/       AI Engine Foundation: composes bootstrap + execution/workflow/agents/plugins
docs/architecture.md  High-level architecture
docs/architecture/    Principles and roadmap
docs/adr/            Architecture Decision Records
docs/specs/           Detailed subsystem specifications
docs/diagrams/        Supporting diagrams
tests/                Test suite (mirrors src/mellivor_kernel structure)
examples/             Minimal, runnable usage examples per subsystem
scripts/              Developer/maintenance scripts
.github/workflows/    CI
pyproject.toml         Package metadata, ruff/mypy/pytest configuration
.pre-commit-config.yaml  Pre-commit hooks
LICENSE               MIT
```

## Development

Requires Python 3.12+.

```bash
pip install -e ".[dev]"
pre-commit install
```

Tests for `providers.claude.ClaudeProvider` and `providers.openai.OpenAIProvider`
require their respective optional `anthropic`/`openai` packages; without
them (plain `[dev]`) those test files skip cleanly rather than failing.
Install `pip install -e ".[dev,anthropic,openai]"` to also exercise them
(CI does this). Neither ever calls a live API — only real SDK types are
used, with a fake client injected in place of network I/O.

```bash
ruff check .          # lint
ruff format .         # format
mypy                  # type-check
pytest                 # test
```

CI (`.github/workflows/ci.yml`) runs the same four checks on every push and
pull request against `main`, on Python 3.12 and 3.13.

## Status

**Stable v1.0.0, v1.1 development underway.** Sprint 27 (persistent
`MemoryStore`) and Sprint 28 (concrete `SecretProvider` backend) have
shipped; see
[`docs/architecture/roadmap.md`](docs/architecture/roadmap.md) for the
approved Sprint 27–31 sequence. The `1.0.0` compatibility promise below is
unchanged — v1.1 sprints are additive, per
[ADR-0005](docs/adr/0005-versioning-strategy.md).

Per [ADR-0005](docs/adr/0005-versioning-strategy.md),
`1.0.0` is reserved for the explicit decision that every responsibility in
ADR-0002 has a stable, documented contract. That decision is recorded in
[ADR-0020](docs/adr/0020-release-decision-v1.0.md), following the scope
classification [ADR-0019](docs/adr/0019-release-readiness-and-scope-lock.md)
established: every `Included in v1.0` responsibility is satisfied, with
richer capability for several of them deliberately deferred rather than
promised by this release (`agents` is a first, deliberately minimal slice;
`security` and `observability` are foundation-only — contracts and
primitives with no concrete secret backend, authentication, encryption,
metrics/tracing vendor, or telemetry export, and neither is consumed by any
other subsystem except where Sprint 17 wired them into
`authorization`/`execution`; `plugin_sdk` is a convenience layer over
`plugins` whose only consumer is `plugins_builtin`, the kernel's first
built-in plugin; `plugin_discovery` adds filesystem discovery but no
marketplace, remote plugins, sandboxing, hot reload, signature
verification, or package installation; `ai_engine` composes the
orchestration chain but adds no business logic, chat feature, prompting,
reasoning, planning, orchestration decision, or provider-selection logic of
its own). See
[`docs/release/v1.0-release-checklist.md`](docs/release/v1.0-release-checklist.md)
and [`RELEASE_NOTES_v1.0.0.md`](RELEASE_NOTES_v1.0.0.md) for the complete
release record, including deferred scope and known limitations.

Implemented so far: `core` (exceptions, the
`ServiceContainer` DI container, structured logging, and the `Kernel`
runtime/lifecycle), `config` (`KernelConfig`, `Environment`, `load_config`),
`providers` (the `BaseProvider` contract, `ProviderRegistry`,
`ProviderFactory`, plus two concrete providers —
`providers.claude.ClaudeProvider`, backed by the Anthropic Messages API
(optional, requires `pip install mellivor-kernel[anthropic]`), and
`providers.openai.OpenAIProvider`, backed by the OpenAI Chat Completions
API (optional, requires `pip install mellivor-kernel[openai]`); neither
exported from `providers.__all__`, each importable explicitly from its
own module; no Gemini/local-model integration yet), `tools` (the `BaseTool`
contract, `ToolRegistry`, the permission model, and the
`ToolExecutionPipeline`, plus three demonstration tools —
`EchoTool`/`HealthCheckTool`/`VersionTool` — that call no external API),
`bootstrap` (`KernelBootstrap`, `BootstrapBuilder`, and the read-only
`RuntimeContext` — the composition layer that assembles the other four
subsystems into a running kernel), `execution` (`ExecutionRequest`,
`ExecutionContext`, `ExecutionResult`, `Dispatcher`, `ExecutionEngine` — the
orchestration layer that dispatches execution to the Tool Runtime or
Provider Runtime; see
[ADR-0006](docs/adr/0006-execution-core-orchestration-layer.md)), and
`authorization` (`AuthorizationEngine`, `PermissionResolver`,
`PermissionSet`, `AuthorizationRequest`, `AuthorizationResult` — decides
whether an execution request is authorized, consulted by `ExecutionEngine`
through a structural contract it never imports `authorization` to use; see
[ADR-0007](docs/adr/0007-authorization-engine-and-execution-decoupling.md)),
`events` (`Event`, `EventBus`, `InMemoryEventBus`, `EventHandler`,
`EventRegistration` — an in-process publish/subscribe abstraction, not a
distributed messaging system; `execution` and `authorization` both publish
lifecycle events through it without depending on any concrete
implementation; see
[ADR-0008](docs/adr/0008-event-bus-and-lifecycle-events.md)), and `memory`
(`Memory`, `MemoryStore`, `MemoryEntry`, `MemoryQuery`, `MemoryResult`,
`InMemoryStore`, `SQLiteMemoryStore` — text-only memory as kernel
infrastructure, with no dependency on any provider; two concrete
`MemoryStore` backends, ephemeral (`InMemoryStore`) and durable/file-backed
(`SQLiteMemoryStore`, standard-library `sqlite3`, no new dependency); execution
may optionally record execution outcomes through either; see
[ADR-0009](docs/adr/0009-memory-subsystem-and-execution-recording.md) and
[ADR-0021](docs/adr/0021-persistent-memory-sqlite-store.md)),
`workflow` (`Workflow`, `WorkflowDefinition`, `WorkflowStep`,
`WorkflowContext`, `WorkflowEngine`, `WorkflowResult` — composes
sequential multi-step runs by delegating every step to `ExecutionEngine`;
never touches a tool or provider directly, and `execution` has no
dependency back on it; see
[ADR-0010](docs/adr/0010-workflow-engine-and-orchestration-boundary.md)),
and a first, deliberately minimal slice of `agents` — Agent Runtime Core
(`Agent`, `AgentDefinition`, `AgentContext`, `AgentEngine`, `AgentResult`
— an agent invokes exactly one workflow by delegating entirely to
`WorkflowEngine`; no planning, reasoning, reflection, or multi-agent
composition yet; see
[ADR-0011](docs/adr/0011-agent-runtime-core-and-orchestration-chain.md)) —
see [`docs/specs/`](docs/specs/README.md) for their public contracts.

Four further foundation-only packages are also implemented: `security`
(`Secret`, `SecretProvider`, `SecretProviderRegistry`, `SecurityPolicy`,
`SecurityDecision`, `SecureConfiguration`, `AuditRecord`, `AuditSink` —
reusable security contracts and primitives, depending only on `core`;
plus, as of Sprint 28, a first concrete `SecretProvider` backend,
`EnvSecretProvider` — read-only, process-environment-backed, standard
library only, no new dependency; still no authentication, OAuth, SSO,
RBAC, or encryption; see
[ADR-0012](docs/adr/0012-security-foundation.md) and
[ADR-0022](docs/adr/0022-env-secret-provider.md)), `observability`
(`ObservationContext`, `MetricsRecorder`, `TraceRecorder`/`TraceSpan`,
`StructuredEventSink`/`StructuredObservationEvent`, no-op default
implementations, and the `Observability` DI wrapper — depending on no
other kernel package; no metrics/tracing backend or telemetry export; see
[ADR-0013](docs/adr/0013-observability-foundation.md)), and `plugins`
(`Plugin`, `PluginMetadata`, `PluginContext`, `PluginCapability`,
`PluginManifest`, `PluginRegistry`, `PluginLoader`, `PluginLifecycle`/
`PluginLifecycleState` — the runtime a plugin is loaded, validated,
registered, and run through, depending only on `core` and the top-level
`version` module; a caller may supply an explicit `PluginManifest` and
constructor directly, or discover one from a filesystem location (below);
see [ADR-0014](docs/adr/0014-plugin-runtime-foundation.md)), `plugin_sdk`
(`PluginBuilder`, `BasePlugin`, `create_capability`/`create_manifest`/
`create_metadata`, `is_valid_capability`/`is_valid_manifest`/
`is_valid_metadata` — a developer-convenience layer over `plugins`,
depending only on it; adds no new contract or validation rule of its
own — every helper delegates to the corresponding `plugins` constructor;
see [ADR-0015](docs/adr/0015-plugin-sdk-foundation.md)), `plugins_builtin`
(`SystemInfoPlugin`, `SystemInfoSnapshot` — the kernel's first built-in
plugin, exposing read-only kernel version, build info, available
capabilities, registered providers/tools, and runtime health; performs
no mutation and no configuration change; see
[ADR-0016](docs/adr/0016-system-info-built-in-plugin.md)), and
`plugin_discovery` (`PluginDiscovery` — discovers plugins from a
filesystem location and loads/registers them through the unmodified
`PluginLoader`/`PluginRegistry`, introducing no new loading, validation,
or registration logic; depends only on `plugins` and `core`; no
marketplace, remote plugins, sandboxing, hot reload, signature
verification, or package installation; see
[ADR-0017](docs/adr/0017-plugin-discovery-foundation.md)), and
`ai_engine` (`AIEngine`, `AIEngineBuilder` — a pure
composition layer assembling an already-bootstrapped `RuntimeContext`
and the orchestration-chain engines (`ExecutionEngine` -> `WorkflowEngine`
-> `AgentEngine`, with an `Authorizer` optionally consulted) plus a
`PluginRegistry`; every operation delegates to the existing engine that
already decides it; depends on `core`, `bootstrap`, `execution`,
`authorization`, `workflow`, `agents`, `memory`, `events`, `security`,
`observability`, `plugins`, and `plugin_discovery`; see
[ADR-0018](docs/adr/0018-ai-engine-foundation.md)). `security` and
`observability` are dependency-injected and structurally separate from
`execution`, `workflow`, `agents`, and `providers`; as of Sprint 17,
`authorization` and `execution` are their first consumers (see below). As
of Sprint 20, `plugin_sdk`'s only consumer is `plugins_builtin`. As of
Sprint 21, `plugin_discovery` loads `plugins_builtin.SystemInfoPlugin`
from a real manifest file without a caller hand-constructing it. As of
Sprint 22, `ai_engine` is the first consumer to compose `execution`,
`workflow`, `agents`, and `authorization` together into one object;
nothing in the kernel itself imports `ai_engine`, `plugin_discovery`, or
`plugins_builtin`.

`bootstrap` still does not wire the newer engines (`ExecutionEngine`,
`AuthorizationEngine`, `WorkflowEngine`, `AgentEngine`) together itself —
that composition now has a concrete, supported mechanism,
`ai_engine.AIEngineBuilder`, built on top of a `RuntimeContext` rather
than each consumer hand-wiring the chain, as every example prior to
Sprint 22 in [`examples/`](examples/) did.

## Contributing

Any change with architectural weight (a new subsystem, a changed contract, a
new dependency, a reversed prior decision) should be preceded by an ADR. See
[`docs/adr/README.md`](docs/adr/README.md) for the process.

No CRM, Legal, HR, Finance, Security, or other business/domain logic will be
accepted into this repository — see
[ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md).

## License

[MIT](LICENSE)
