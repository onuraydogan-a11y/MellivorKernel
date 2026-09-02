# Sprint 40: Observability, metrics, and tracing integration boundary

Status: Architecture Challenge complete — product/deployment adapter responsibility

Date: 2026-09-02

## Decision

**C — PRODUCT / DEPLOYMENT ADAPTER RESPONSIBILITY.**

Mellivor Kernel already owns the vendor-neutral observability boundary that its
runtime needs: standard structured logging, correlation context, minimal
metrics and tracing Protocols, a structured-event sink, no-op implementations,
and dependency-injected execution lifecycle observations. Kernel must not add
an OpenTelemetry, Prometheus, or commercial-vendor adapter now.

This is an evidence-based boundary, not a dismissal of telemetry. Mellivor AI
Security has implemented real product observability by adapting the existing
`StructuredEventSink` to standard logging and by owning its HTTP metrics and
health behavior. Mellivor One's future VIP architecture selects OpenTelemetry
for service instrumentation, but the current product has neither an
OpenTelemetry dependency nor a Kernel observability adapter. These consumers
have different maturity, signals, privacy rules, and deployment lifecycles;
neither demonstrates a missing reusable Kernel contract.

No technology, type, module, dependency, implementation ADR, or public API is
approved. A future consumer may implement an adapter against the existing
Protocols and own its SDK/runtime explicitly. Evidence from two consumers that
the same safe translation is being duplicated would justify reassessing a
shared library before adding anything to Kernel.

## Scope and sources

The audit covered ADR-0002/0003 boundaries, ADR-0005 SemVer, ADR-0013, the
v1.0 scope decisions, architecture/specification documents, release audits,
roadmap Future Research, the complete `observability` package and tests,
logging/configuration/bootstrap, `ExecutionEngine`, `AIEngineBuilder`, event
relationships, and provider/tool/plugin/workflow/agent call sites. Consumer
evidence was reviewed read-only from the sibling `MellivorAISecurity` and
`MellivorOne` repositories.

## Existing observability architecture

### Structured logging

`core.logging` uses Python's standard `logging` hierarchy. A
`StructuredFormatter` produces JSON lines with UTC timestamp, severity, logger,
message, and formatted exception information. `configure_logging` configures
the `mellivor_kernel` logger explicitly and idempotently; `get_logger` creates
namespaced loggers; `add_file_handler` is caller-directed. Kernel has no log
shipper, remote endpoint, batching thread, credential, or retention policy.

The message field is still caller-generated text. Structured formatting is not
automatic redaction, so callers and Kernel instrumentation must continue to
avoid placing sensitive values in messages or exception text.

### Neutral observation contracts

ADR-0013 established these public, structural contracts:

- `ObservationContext`: correlation ID plus optional trace ID, span ID, and
  attributes;
- `MetricsRecorder.increment`: a counter-style numeric observation;
- `TraceRecorder.start_span` and `TraceSpan.end`: a minimal span lifecycle;
- `StructuredEventSink.emit`: a generic structured observation sink;
- `StructuredObservationEvent`: name, message, context, and attributes; and
- `Observability`: explicit composition with no-op defaults.

The package depends on no telemetry SDK or other Kernel subsystem. It performs
no import-time setup and owns no background work. `MetricsRecorder`,
`TraceRecorder`, `TraceSpan`, and the `Observability` wrapper remain unproven by
production Kernel call sites. This known v1.x status was explicitly ratified
during the public API freeze.

### Runtime instrumentation

`ExecutionEngine` accepts an optional `StructuredEventSink` and emits
`execution.started`, `execution.completed`, or `execution.failed` alongside
its independent `EventBus` lifecycle publication. It correlates these records
with `ExecutionRequest.request_id`. Completion includes elapsed time; failures
include error and stage. The `AIEngineBuilder` passes a caller-supplied sink
through to execution.

Workflow, agent, provider, tool, plugin, authorization, and EventBus internals
do not call `MetricsRecorder` or `TraceRecorder`, and they do not create span
hierarchies. Provider/tool activity is observable indirectly at the execution
boundary, but there are no dedicated provider-call, tool-call, retry, or
parallel-workflow spans. Kernel bootstrap does not construct an external
telemetry runtime.

### Event, audit, and health separation

- `EventBus` is synchronous in-process lifecycle notification, not telemetry
  export.
- `AuditSink` receives security authorization records, not operational logs or
  metrics.
- `StructuredEventSink` receives execution observations, not durable audit or
  business events.
- Health/readiness endpoints are application/deployment concerns; Kernel's
  built-in system information health is not an HTTP probe framework.
- Product analytics are outside Kernel.

These seams must remain separate even when a product correlates them.

## Consumer evidence

### Mellivor AI Security

This is concrete implementation evidence:

- accepted product ADR-0040 separates operational telemetry from durable
  security audit and permits correlation only by safe request ID;
- `LoggingStructuredEventSink` structurally implements Kernel's existing sink
  using stdlib logging, is injected into the Kernel composition root, suppresses
  sink failures, and deliberately ignores event attributes;
- product middleware records method/path, status, latency, public request ID,
  enforcement outcome, and coarse failure category after response delivery;
- `InProcessMetrics` owns thread-safe process-local aggregate counters and
  average latency, exposed through the product's `/metrics` route;
- `/healthz` and `/readyz` are product-owned HTTP endpoints; and
- current package dependencies contain no OpenTelemetry, Prometheus, Datadog,
  New Relic, Grafana, Application Insights, or telemetry exporter SDK.

Deployment evidence supports SaaS, Private Cloud, and On-Prem operation without
a mandatory external telemetry service. Operational export destination,
collector, retention, dashboards, and alerting are not selected in the
evidence reviewed. Kernel-generated execution observations are useful, but the
existing sink already supplies them.

AI Security therefore proves that product-owned adaptation is viable. Its
aggregate HTTP metrics are deliberately product semantics and do not implement
Kernel's generic `MetricsRecorder`.

### Mellivor One

Mellivor One's VIP architecture ADR-007 accepts OpenTelemetry as the future
instrumentation standard across services so that SaaS, Private Cloud, air-gap,
and government-cloud deployments may choose different backends. It anticipates
metrics, logs, distributed traces, sampling, and correlated diagnosis.

That is credible near-term architecture evidence, but it is not current
implementation evidence for a Kernel adapter:

- current Python dependency manifests contain Flask, Gunicorn, PostgreSQL
  support, and other product libraries, but no OpenTelemetry or telemetry
  exporter dependency;
- current Kernel integration documentation composes runtime, memory, EventBus,
  workflow, and agents without an observability sink;
- no current code reference to Kernel `MetricsRecorder`, `TraceRecorder`,
  `ObservationContext`, or `StructuredEventSink` was found; and
- the VIP document deliberately leaves deployment-specific telemetry backends
  to topology selection.

The product's UI “execution trace” is an application-visible execution-step
record, not an OpenTelemetry distributed trace and not evidence for a Kernel
span API change.

### Other consumers

No other repository evidence identifies a current Kernel consumer with a
telemetry SDK, collector, exporter, or duplicated Kernel adapter. The website
and CRM repositories do not establish a reusable Kernel telemetry need.

## Concern boundaries

| Concern | Current owner | Decision |
|---|---|---|
| Structured Kernel logs | Kernel | Keep standard logging and safe messages |
| Correlation propagation | Kernel at its runtime boundary; product across transports | Keep `ObservationContext` and request IDs; do not invent transport propagation |
| Trace spans | Existing neutral Kernel Protocol, currently unused | Consumers may adapt; do not add SDK integration or instrumentation now |
| Metrics | Existing minimal Kernel Protocol plus product-owned metrics | Kernel names no external metric series now |
| Authorization audit | Kernel security seam and product persistence | Never route through operational telemetry by default |
| Security events | Product | Preserve privacy and tenant policy in product code |
| Product analytics | Product | Outside Kernel |
| Health/readiness | Product/deployment | Application-specific dependency checks and routes |
| Vendor export | Product/deployment | Own SDK, endpoint, credentials, lifecycle, and retention |

## OpenTelemetry assessment

OpenTelemetry is a vendor-neutral telemetry standard, but its neutrality does
not make its SDK a Kernel responsibility.

- The API defines instrumentation-facing concepts; the SDK owns processors,
  samplers, readers, batching, aggregation, and provider configuration.
- OTLP exporters introduce endpoints, credentials, TLS, retry, queueing,
  shutdown, and failure behavior.
- language SDKs commonly expose global providers and context propagation, while
  exporters may start threads and buffer data.
- trace and baggage propagation across HTTP or messaging boundaries belongs to
  the product transport that understands trust and tenant boundaries.
- resource attributes, sampling, collector topology, and export policy differ
  across SaaS, Private Cloud, On-Prem, air-gap, and government environments.

The selected conceptual posture is **C: retain existing neutral seams and let
products adapt them**. OpenTelemetry is evidence-backed as Mellivor One's
future product standard, but is not selected as a Kernel technology.

If a future adapter is built, its caller must construct and configure the SDK,
inject the adapter explicitly, and own force-flush/shutdown. Kernel must not
set a global provider, replace an existing provider, start an exporter or
collector, read telemetry credentials, or register shutdown hooks silently.
An adapter must remain inert until called and must not make network access at
import or construction time.

## Metrics semantics and cardinality

The current `MetricsRecorder.increment` contract exposes only a metric name,
numeric value, and optional context. Kernel has not declared stable external
metric names, units, descriptions, histogram boundaries, or label keys. Its
shape should not be reinterpreted as an OpenTelemetry/Prometheus semantic
convention without a separate evidence-backed decision.

Generic safeguards for any future instrumentation:

- allow only bounded, documented labels such as operation category, execution
  target type, coarse outcome, and stable error category;
- never label with prompt/input/output text, embeddings, vectors, arbitrary
  metadata, secrets, credentials, headers, authorization tokens, exception or
  response bodies, endpoint URLs containing user data, tool arguments/results,
  or private reasoning;
- never use request, correlation, trace, span, tenant, user, record, session,
  or caller-owned IDs as metric labels;
- do not use unrestricted provider model names, tool/plugin names, error
  strings, or caller operations unless converted to an explicit bounded
  allowlist; and
- reject or drop non-finite numeric observations in a future concrete adapter.

Correlation IDs belong in logs/traces where access is controlled, not in
metric labels. Tenant/user identifiers require product data-classification and
must not be emitted merely because `ObservationContext.attributes` can hold
arbitrary values.

## Tracing semantics

Current correlation is useful but is not a complete distributed tracing
model. `ExecutionEngine` creates a fresh context containing only the request ID;
it does not propagate caller trace/span IDs. `TraceRecorder` can start and end
a span but cannot record status, events, attributes, parentage, exceptions, or
context-manager behavior. Parallel workflow branches and provider/tool calls
therefore have no defined span hierarchy.

This narrowness is not authorization to expand frozen v1.x contracts without
dogfood. A product-owned adapter can convert structured execution events into
safe events/logs today. If real tracing later needs richer semantics, the
consumer must first demonstrate required propagation and lifecycle behavior;
that may warrant an additive sibling contract or a future major-version
change, but Sprint 40 approves neither.

No trace may contain prompts, provider responses, tool payloads, credentials,
raw exception bodies, vectors/embeddings, private reasoning, or arbitrary
metadata by default. Retry and parallel-branch spans must reflect observable
operations only, never hidden chain-of-thought.

## Logging boundary

Kernel should continue emitting through standard logging and its existing
structured event sink. Standard handlers already let a consumer route records
to its chosen runtime without a proprietary Kernel log pipeline. A product may
adapt records or structured observations to OpenTelemetry logs, a SIEM, or
another collector under its own redaction and retention policy.

Kernel must not configure root logging, install vendor handlers, ship logs,
own rotation/retention beyond an explicitly requested local handler, or claim
that exception formatting is safe for remote export.

## Security and privacy boundary

Kernel responsibilities are limited to safe-by-design event content, no
credential ownership, explicit injection, and preserving authorization as the
execution gate. Telemetry is observational and never grants authority.

Products/deployments own data classification, tenant/user pseudonymization,
collector trust, TLS, broker/network policy, access control, encryption,
sampling, storage region, retention, deletion, dashboards, alerting, and
incident access. A received or propagated trace context is untrusted metadata;
it must not select a tenant, grant permissions, or bypass authorization.

Redaction must happen before an event crosses the sink boundary. Exporters
cannot be relied on to repair unsafe instrumentation. Telemetry failures must
not expose raw payloads through fallback logs and must not turn a security
deny into an allow. Conversely, a product may choose fail-closed readiness for
a required collector, but Kernel must not impose collector availability on AI
execution.

## Failure, lifecycle, and global-state boundary

The existing synchronous sink runs on the execution path and does not define
failure isolation: an arbitrary sink exception can currently escape. AI
Security deliberately suppresses its adapter failures. Whether to buffer,
drop, retry, block, sample, or fail readiness is operational policy and must
not be hidden behind the current Protocol.

Any future telemetry runtime must be caller-owned:

- explicit construction and injection;
- bounded buffers and documented drop behavior;
- caller-selected synchronous or batching processors;
- explicit flush timeout and shutdown order;
- no implicit singleton/global-provider mutation;
- no hidden background lifecycle in Kernel; and
- deterministic no-network fakes for tests.

These requirements are compatible with a product adapter but are not expressed
by current Kernel contracts. Adding them now would create a second lifecycle
framework without consumer proof.

## Candidate architecture

No new architecture is approved. The current path remains:

```text
Kernel standard logs / StructuredEventSink / neutral Protocols
    -> product-owned adapter
    -> caller-owned telemetry SDK/runtime
    -> deployment-owned collector/export destination
```

### Proposed types and modules

None. `TraceExporter`, `MetricsExporter`, `TelemetrySink`, `SpanProcessor`, and
`MetricsSink` would either duplicate existing Protocols or import SDK lifecycle
semantics into Kernel. No `observability.opentelemetry` module or optional
dependency extra is justified.

A reusable adapter discovered in two products should first live in a shared
library, with explicit SDK objects passed into it. Only repeated evidence that
Kernel-specific event translation cannot be maintained outside Kernel would
justify a Proposed ADR for an optional internal adapter.

## Compatibility and public API

The decision requires zero change to `ObservationContext`, `MetricsRecorder`,
`TraceSpan`, `TraceRecorder`, `StructuredEventSink`,
`StructuredObservationEvent`, `Observability`, `ExecutionEngine`, workflow,
providers, tools/plugins, `EventBus`, configuration, or bootstrap. It is fully
compatible with v1.x and requires no major version.

The existing observability contracts remain public and stable as frozen in
v1.0; Sprint 40 adds no public names and does not reinterpret their semantics.
A future product adapter can be implemented additively outside Kernel. A future
Kernel adapter could also be additive if it merely implements an existing
Protocol and keeps lifecycle caller-owned. Changing Protocol method signatures
or silently introducing global SDK behavior would require separate SemVer and
architecture review.

## Risks

- Current `ObservationContext.attributes` and event attributes accept arbitrary
  Python values and are not inherently immutable, serializable, bounded, or
  redacted; adapters must treat them as untrusted.
- Execution failure event messages and attributes may contain error text;
  direct remote export can leak provider/tool detail unless a product filters
  it. AI Security's sink ignores attributes but still logs the message.
- `MetricsRecorder`/`TraceRecorder` remain stable yet undogfooded public
  contracts and may be too small for real OpenTelemetry semantics.
- Products can produce inconsistent metric names and trace hierarchies when
  they adapt independently.
- In-process metrics reset on restart and do not aggregate across workers;
  this is an AI Security product limitation, not a Kernel defect.
- A future Mellivor One deployment may reveal cross-process propagation or
  shutdown requirements not visible in current code.

## Open questions and reassessment triggers

Reassess only when a consumer supplies a concrete deployment with:

1. an implemented telemetry SDK and collector topology;
2. a demonstrated need for Kernel execution/provider/tool spans or metrics;
3. approved safe metric names, units, attributes, and cardinality budgets;
4. trace-context ingress/egress and tenant-isolation rules;
5. sampling, buffering, failure, flush, and shutdown requirements;
6. Private Cloud/On-Prem or air-gap lifecycle evidence; and
7. evidence that the same adapter logic is duplicated across products.

The first practical evidence candidate is Mellivor One's future OpenTelemetry
deployment. Its adapter should initially remain product-owned. AI Security's
existing stdlib sink and aggregate metrics should remain unchanged unless that
product independently approves a different telemetry runtime.
