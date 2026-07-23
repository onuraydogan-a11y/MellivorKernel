# 0013. Introduce a dedicated `observability` subsystem for reusable kernel observability primitives

Status: Accepted
Date: 2026-07-23

## Context

ADR-0002 names **Observability** as a fixed kernel responsibility, but the
kernel still lacks a reusable package owning even the minimum contracts for
metrics, traces, structured events, and correlation propagation. The release
audit identified this as the next priority milestone after security.

A future `1.0.0` release needs stable, dependency-injected primitives for
observation metadata and event emission without coupling the kernel to any
telemetry vendor or monitoring product. The repository boundary rules require
that the kernel remain business-agnostic and keep product observability
concerns outside the kernel's own package surface.

## Decision

Introduce a new top-level package,
`src/mellivor_kernel/observability/`, whose responsibility is limited to a
foundation-only observability substrate:

- observation contracts
- metrics abstraction
- tracing abstraction
- structured event abstraction
- correlation ID support
- observation context
- no-op implementations
- dependency injection wiring

This package is intentionally not a telemetry platform. It does not include
any exporter, backend, dashboard, or vendor-specific integration. It remains
small, dependency-injected, backward compatible, and separate from
`execution`, `workflow`, `agents`, `providers`, and product orchestration
logic.

## Consequences

- The kernel now owns a minimal, reusable observability contract surface that
  future instrumentation can build on safely.
- Consumers can compose metrics, tracing, and event sinks explicitly through
  dependency injection rather than by introducing new kernel-wide coupling.
- The package remains compatible with ADR-0002 and ADR-0003 because it stays
  kernel-owned infrastructure and never turns into a product monitoring
  subsystem.
