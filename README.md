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
- Not, at this stage, a working implementation — see [Status](#status) below.

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
docs/architecture.md  High-level architecture
docs/architecture/    Principles and roadmap
docs/adr/            Architecture Decision Records
docs/specs/           Detailed subsystem specifications
docs/diagrams/        Supporting diagrams
tests/                Test suite (mirrors src/mellivor_kernel structure)
examples/             Minimal usage examples, once the kernel exists
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

```bash
ruff check .          # lint
ruff format .         # format
mypy                  # type-check
pytest                 # test
```

CI (`.github/workflows/ci.yml`) runs the same four checks on every push and
pull request against `main`, on Python 3.12 and 3.13.

## Status

**Foundation stage.** Implemented so far: `core` (exceptions, the
`ServiceContainer` DI container, structured logging, and the `Kernel`
runtime/lifecycle), `config` (`KernelConfig`, `Environment`, `load_config`),
`providers` (the `BaseProvider` contract, `ProviderRegistry`,
`ProviderFactory` — interfaces and registry only, no concrete OpenAI/
Anthropic/Gemini/local-model integration), `tools` (the `BaseTool`
contract, `ToolRegistry`, the permission model, and the
`ToolExecutionPipeline`, plus three demonstration tools —
`EchoTool`/`HealthCheckTool`/`VersionTool` — that call no external API),
`bootstrap` (`KernelBootstrap`, `BootstrapBuilder`, and the read-only
`RuntimeContext` — the composition layer that assembles the other four
subsystems into a running kernel), and `execution` (`ExecutionRequest`,
`ExecutionContext`, `ExecutionResult`, `Dispatcher`, `ExecutionEngine` — the
orchestration layer that dispatches execution to the Tool Runtime or
Provider Runtime; see
[ADR-0006](docs/adr/0006-execution-core-orchestration-layer.md)) — see
[`docs/specs/`](docs/specs/README.md) for their public contracts.
`agents`, `workflow`, `memory`, `events`, and `plugins` remain unimplemented
package skeletons. Subsystems are implemented one at a time; do not depend
on this repository for production
use yet.

## Contributing

Any change with architectural weight (a new subsystem, a changed contract, a
new dependency, a reversed prior decision) should be preceded by an ADR. See
[`docs/adr/README.md`](docs/adr/README.md) for the process.

No CRM, Legal, HR, Finance, Security, or other business/domain logic will be
accepted into this repository — see
[ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md).

## License

[MIT](LICENSE)
