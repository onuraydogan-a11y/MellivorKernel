# `core` subsystem spec

Status: Implemented (Sprint 2)

Public contract exported from `mellivor_kernel.core`. Anything not listed
here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## Exceptions

- `KernelError` — base class for every exception the kernel raises.
- `ConfigurationError` — invalid, missing, or malformed configuration.
- `ServiceRegistrationError` — a service container registration or lookup
  failure.
- `StartupError` — the kernel failed to start, or a lifecycle method was
  called from an invalid state.

## `KernelSettings` (contract)

A structural `Protocol` (`core.contracts`) exposing a single read-only
`log_level: str` property. `core` depends on this shape rather than
importing `mellivor_kernel.config` directly, so that `core` has no
dependency on subsystems that depend on it (`config.KernelConfig` satisfies
this protocol without either module importing the other).

## `ServiceContainer`

A lightweight, type-safe dependency injection container.

- `register(service_type, factory, *, singleton=True)` — register a
  zero-argument factory. Raises `ServiceRegistrationError` if
  `service_type` is already registered.
- `register_instance(service_type, instance)` — register an
  already-constructed instance as a singleton.
- `resolve(service_type)` — resolve an instance. Singleton factories run at
  most once, lazily, on first resolution. Non-singleton factories run on
  every call. Raises `ServiceRegistrationError` if unregistered.
- `is_registered(service_type)` — check registration without resolving.

## Logging

- `configure_logging(settings: KernelSettings) -> logging.Logger` —
  configures the `mellivor_kernel` root logger's level and console handler
  from `settings.log_level`. Idempotent: re-running it replaces only the
  console handler it owns, leaving file handlers attached via
  `add_file_handler` untouched. Raises `ConfigurationError` for an invalid
  level name.
- `get_logger(name: str) -> logging.Logger` — returns a logger namespaced
  under `mellivor_kernel.<name>`.
- `add_file_handler(logger, path, *, level=None) -> logging.Handler` — a
  minimal file handler, creating parent directories as needed.
- `StructuredFormatter` — renders log records as single-line JSON.

This is the current, minimal placement of the "Observability" kernel
responsibility named in [ADR-0002](../adr/0002-ai-enterprise-kernel-scope-and-subsystems.md),
per that ADR's own stated fallback ("hosted inside `core/`"). It covers
structured logging only; tracing, metrics, and audit trail remain
unaddressed and unplaced.

## `Kernel` (runtime)

Owns a `ServiceContainer` and manages kernel lifecycle.

- `Kernel(settings: KernelSettings, container: ServiceContainer | None = None)`
  — `container` defaults to a new, empty `ServiceContainer` if omitted.
- `.container` — the kernel's service container.
- `.state` — current `KernelState`.
- `.start()` — runs the startup sequence (configures logging from
  `settings`). Valid from `NOT_STARTED`, `STOPPED`, or `FAILED` (retry).
  Raises `StartupError` from any other state, or if startup itself fails
  (transitioning to `FAILED`).
- `.shutdown()` — runs the shutdown sequence. Idempotent: a no-op unless
  the kernel is currently `RUNNING`.
- `.health() -> HealthStatus` — a point-in-time `{healthy, state, detail}`
  report.

`KernelState`: `NOT_STARTED`, `STARTING`, `RUNNING`, `STOPPING`, `STOPPED`,
`FAILED`.
