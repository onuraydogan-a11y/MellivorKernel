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
- Not yet a complete implementation of every responsibility in
  [ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md)
  — see [Status](#status) below for exactly what is and isn't
  implemented.

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
    plugins/         Plugin loading
    config/          Configuration
    providers/       Multi-LLM provider abstraction
    bootstrap/       Composition layer: assembles core/config/providers/tools
    execution/       Execution orchestration: request/context/result, dispatch, engine
    authorization/   Permission-based authorization for execution requests
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

Tests for `providers.claude.ClaudeProvider` require the optional
`anthropic` package; without it (plain `[dev]`) those two test files
skip cleanly rather than failing. Install
`pip install -e ".[dev,anthropic]"` to also exercise them (CI does this).
They never call the live API — only real `anthropic` SDK types are used,
with a fake client injected in place of network I/O.

```bash
ruff check .          # lint
ruff format .         # format
mypy                  # type-check
pytest                 # test
```

CI (`.github/workflows/ci.yml`) runs the same four checks on every push and
pull request against `main`, on Python 3.12 and 3.13.

## Status

**Release Candidate (v0.13.0).** Not yet `1.0.0` — per
[ADR-0005](docs/adr/0005-versioning-strategy.md), that version number is
reserved for an explicit future decision once every responsibility in
ADR-0002 is stable, which is not yet the case (`plugins` is unimplemented;
`agents` is a first, deliberately minimal slice; Security primitives and
most of Observability remain unaddressed). See
[`docs/release/v1.0-release-checklist.md`](docs/release/v1.0-release-checklist.md)
for the complete release-readiness assessment, including known
limitations.

Implemented so far: `core` (exceptions, the
`ServiceContainer` DI container, structured logging, and the `Kernel`
runtime/lifecycle), `config` (`KernelConfig`, `Environment`, `load_config`),
`providers` (the `BaseProvider` contract, `ProviderRegistry`,
`ProviderFactory`, plus one concrete provider —
`providers.claude.ClaudeProvider`, backed by the Anthropic Messages API;
optional, requires `pip install mellivor-kernel[anthropic]`; no OpenAI/
Gemini/local-model integration yet), `tools` (the `BaseTool`
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
`InMemoryStore` — text-only memory as kernel infrastructure, with no
dependency on any provider; `execution` may optionally record execution
outcomes through it; see
[ADR-0009](docs/adr/0009-memory-subsystem-and-execution-recording.md)),
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
`plugins` remains an unimplemented package skeleton. Bootstrap does not
yet wire the newer engines (`ExecutionEngine`, `AuthorizationEngine`,
`WorkflowEngine`, `AgentEngine`) together automatically — a consumer
composes them explicitly, as every example in [`examples/`](examples/)
does.

## Contributing

Any change with architectural weight (a new subsystem, a changed contract, a
new dependency, a reversed prior decision) should be preceded by an ADR. See
[`docs/adr/README.md`](docs/adr/README.md) for the process.

No CRM, Legal, HR, Finance, Security, or other business/domain logic will be
accepted into this repository — see
[ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md).

## License

[MIT](LICENSE)
