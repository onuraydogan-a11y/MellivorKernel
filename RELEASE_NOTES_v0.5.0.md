# Mellivor Kernel v0.5.0

Tag: `v0.5.0` · Commit: `138706e` · Branch: `main`

Foundation-stage release. Five sprints of implementation on top of the
architecture established in Sprints 0–1 (ADR-0001 through ADR-0005,
package skeleton, tooling). Not yet suitable for production use — see
[Known limitations](#known-limitations).

## Completed subsystems

| Subsystem | Sprint | Summary |
|---|---|---|
| `core` | 2 | Exception hierarchy, `ServiceContainer` (DI), structured logging, `Kernel` runtime/lifecycle |
| `config` | 2 | `KernelConfig`, `Environment`, `load_config()` (environment-variable loading) |
| `providers` | 3 | `BaseProvider` contract, `ProviderRegistry`, `ProviderFactory` — interfaces and registry only, **no concrete provider implementation exists** |
| `tools` | 4 | `BaseTool` contract, `ToolRegistry`, the permission model, `ToolExecutionPipeline`, three demonstration tools (`EchoTool`/`HealthCheckTool`/`VersionTool`) |
| `bootstrap` | 5 | `KernelBootstrap`, `BootstrapBuilder`, read-only `RuntimeContext` — composes the four subsystems above into a running kernel |

**Not implemented:** `agents`, `workflow`, `memory`, `events`, `plugins` —
empty package skeletons only. Security primitives and most of
Observability (tracing, metrics, audit trail) are entirely unaddressed,
with no package or code.

Full per-subsystem contracts: `docs/specs/{core,config,providers,tools,bootstrap}.md`.

## Public APIs

60 exported symbols across 7 importable modules, all verified importable
against their `__all__` at release time:

- **`mellivor_kernel`** (1): `__version__`
- **`mellivor_kernel.core`** (13): `KernelError`, `ConfigurationError`, `ServiceRegistrationError`, `StartupError`, `KernelSettings`, `ServiceContainer`, `Kernel`, `KernelState`, `HealthStatus`, `StructuredFormatter`, `configure_logging`, `get_logger`, `add_file_handler`
- **`mellivor_kernel.config`** (4): `ConfigurationError`, `Environment`, `KernelConfig`, `load_config`
- **`mellivor_kernel.providers`** (9): `ProviderError`, `ProviderConfigurationError`, `ProviderRegistrationError`, `BaseProvider`, `ProviderCapabilities`, `ProviderConfiguration`, `ProviderHealthCheck`, `ProviderRegistry`, `ProviderFactory`
- **`mellivor_kernel.tools`** (16): `ToolError`, `ToolRegistrationError`, `ToolValidationError`, `Permission`, `NETWORK_READ`, `FILESYSTEM_READ`, `FILESYSTEM_WRITE`, `PROVIDER_INVOKE`, `KERNEL_INTERNAL`, `missing_permissions`, `BaseTool`, `ToolContext`, `ToolMetadata`, `ToolResult`, `ToolRegistry`, `ToolExecutionPipeline`
- **`mellivor_kernel.tools.builtin`** (3): `EchoTool`, `HealthCheckTool`, `VersionTool`
- **`mellivor_kernel.bootstrap`** (4): `KernelBootstrap`, `BootstrapBuilder`, `RuntimeContext`, `BootstrapError`

## Architecture summary

```
config  providers  tools  ──depend on──>  core
                     bootstrap  ──depends on──>  core, config, providers, tools
```

- **`core` depends on nothing else in the package.** Load-bearing
  invariant since Sprint 2: every other implemented subsystem depends only
  on `core`, never on each other, so the dependency graph stays acyclic.
- **`bootstrap`** is the one exception, by necessity: it composes all four
  subsystems into a running kernel, which is why it's a new top-level
  package rather than living inside any one of them (see
  `docs/specs/bootstrap.md` and the "composition layer" section of
  `docs/architecture.md`).
- Two interface styles coexist deliberately: `KernelSettings` (structural
  `Protocol`, used for dependency inversion so `core` never imports
  `config`) versus `BaseProvider`/`BaseTool` (nominal `ABC`, since concrete
  implementations are expected to literally subclass them).
- `RuntimeContext.tool_context()` is the supported way to run a tool
  against a bootstrapped kernel: it builds a `ToolContext` using
  `RuntimeContext`'s private `Kernel` reference internally, without ever
  exposing that `Kernel` to the caller.

Full architecture decisions: `docs/adr/0001`–`0005`; current-state summary:
`docs/architecture.md`.

## Breaking changes

**None.** Every sprint from `core`/`config` (Sprint 2) onward has been
strictly additive. Verified for this release: `git diff` of `core`,
`config`, `providers`, `tools`, the top-level package, and `pyproject.toml`
against the pre-Sprint-5 commit shows zero changes to any existing file's
content — only new files were added, across every sprint in this release.

## Known limitations

- **`RuntimeContext` has no `shutdown()`.** Nothing returned by
  `bootstrap`'s public API can gracefully stop a bootstrapped kernel — a
  deliberate, conservative reading of "read-only view, prevent mutation"
  from Sprint 5, left open rather than resolved either way.
- **No concrete `BaseProvider` implementation exists anywhere.** The
  provider contract is exercised only by test doubles; its real-world
  shape (retries, timeouts, streaming, tool-calling, error translation for
  a real SDK) is unproven.
- **`providers` and `tools` have no defined relationship.**
  `PROVIDER_INVOKE` exists as a tools-subsystem permission constant, but
  nothing wires a tool to actually call a provider yet.
- **Granted-permissions provenance is unspecified.**
  `ToolExecutionPipeline.run(..., granted_permissions=...)` takes the
  grant set as a bare argument; no subsystem yet owns *deciding* what's
  granted to a given execution.
- **Security primitives are entirely unaddressed** — no package, no code,
  no design. Named as a kernel responsibility in ADR-0002, unresolved
  since.
- **Observability is one-third built** — structured logging only; no
  tracing, metrics, or audit trail.
- **No production bootstrap entry point beyond `bootstrap` itself has been
  exercised by anything except tests.** No real consuming application
  (e.g. Mellivor One) has integrated against this kernel yet.

## Sprint roadmap (6–10)

Moved to [`docs/architecture/roadmap.md`](docs/architecture/roadmap.md)
(Sprint 5 docs reorganization), so the roadmap can be kept current as a
living document instead of frozen inside this release's notes. The content
below reflects what was approved at the time of this release; see that
file for the current version.
