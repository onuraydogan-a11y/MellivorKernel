# `observability` subsystem spec

Status: Foundation (Sprint 16)

This sprint defines the kernel's reusable observability foundation. It does
not implement a telemetry backend, metrics engine, tracing vendor, or product
monitoring stack.

## Scope

The new package is intended to provide only the smallest reusable substrate
required for future kernel and product integrations:

- observation contracts
- metrics abstraction
- tracing abstraction
- structured event abstraction
- correlation ID support
- observation context
- no-op implementations
- dependency injection wiring

The subsystem remains business-agnostic and dependency-injected. It does not
add any product monitoring, distributed tracing vendor integration, or
telemetry export behavior.

## Public contracts

### `ObservationContext`

A lightweight immutable context carrying correlation metadata and optional
trace/span IDs. It is designed to propagate request-scoped metadata across
kernel boundaries without coupling the runtime to any specific backend.

### `MetricsRecorder`

A tiny protocol for emitting metric observations. The kernel remains agnostic
about the actual metrics implementation, whether in-process, a vendor SDK, or
another future sink.

### `TraceRecorder` and `TraceSpan`

A low-friction span contract for creating and ending spans using the
dependency-injected recorder supplied by a consuming application.

### `StructuredEventSink`

An interface for recording structured observation events without binding the
kernel to a particular event system.

### `StructuredObservationEvent`

A serializable event record carrying a name, message, observation context, and
attribute payload.

## No-op default behavior

The package offers no-op implementations so that the core kernel can ship a
foundation with no mandatory backend configuration. All backend-specific
concerns remain out of the `mellivor_kernel` package boundary.
