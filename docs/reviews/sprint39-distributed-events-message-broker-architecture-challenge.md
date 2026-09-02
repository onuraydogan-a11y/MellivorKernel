# Sprint 39: Distributed events and message-broker boundary

Status: Architecture Challenge complete — product/deployment responsibility

Date: 2026-09-02

## Decision

**D — PRODUCT / DEPLOYMENT RESPONSIBILITY.**

Mellivor Kernel must retain its existing synchronous, in-process `EventBus`
unchanged. It must not add distributed-event primitives, a broker adapter,
durable queues, outboxes, workers, serialization contracts, or message
envelopes now.

Current consumers have real multi-process, audit-export, webhook, and durable
state concerns, but they solve them through product-owned repositories, HTTP
boundaries, and deployment topology. None requires delivery of Kernel
lifecycle events across processes. Broker delivery semantics are inseparable
from product transaction boundaries, tenant routing, retention, replay,
idempotency, and operational ownership; placing them in Kernel now would
generalize across requirements that are deliberately different.

No technology is selected. A PostgreSQL outbox is evidence-backed for bounded
product transactions where a product already owns PostgreSQL, but it is a
product persistence pattern, not a Kernel event transport. Kafka, RabbitMQ,
Redis Streams, NATS, and other broker services have no current Mellivor
deployment or operator evidence.

## Scope and evidence

The audit covers ADR-0002/0003 repository boundaries, ADR-0005 SemVer,
ADR-0008 event semantics, lifecycle-event publishers, execution, dispatch,
workflow, agents, authorization, tools, plugins, memory, observability,
configuration, bootstrap, release scope, Future Research, and Sprint 34–38
decisions. Consumer evidence was reviewed read-only from the sibling
`MellivorAISecurity` and `MellivorOne` repositories.

## Existing event architecture

### Core contracts

- `Event` is an immutable, slotted, keyword-only base carrying a generated
  `event_id` and UTC `occurred_at`. Concrete subsystem events add payload
  fields.
- `EventHandler` is a synchronous structural Protocol with
  `handle(event) -> None`.
- `EventBus` is a synchronous structural Protocol with `publish`, `subscribe`,
  and `unsubscribe`.
- `EventRegistration` is an immutable opaque subscription handle containing
  the exact event type and a generated registration ID.
- `InMemoryEventBus` is the only implementation.

### In-process delivery semantics

- Publication invokes handlers synchronously in the publishing thread.
- Subscriptions match the exact concrete event type; base-type subscribers do
  not receive subclasses.
- Handlers run in subscription order within one bus instance.
- No subscriber is a silent no-op.
- A handler exception is caught and logged; publication continues to remaining
  handlers and does not fail the publisher.
- Unsubscribe requires an active registration issued by that bus and fails for
  stale/foreign registrations.
- State is process-local and nonpersistent. Restart loses subscriptions and
  undelivered history.
- There is no cross-process ordering, acknowledgement, retry, replay,
  backpressure, bounded queue, delivery receipt, serialization, consumer
  identity, schema registry, or shutdown lifecycle.

The current bus solves deterministic, lightweight lifecycle notification to
already-running collaborators inside one process. It deliberately does not
solve durable messaging.

### Event ownership and publishers

Each subsystem owns its event types rather than centralizing a universal
payload schema:

- execution publishes started/completed/failed around authorization and
  dispatch;
- authorization publishes granted/denied decisions and separately writes
  security audit records when configured;
- workflow publishes started/completed/failed around multiple executions;
- agents publish started/completed/failed around one delegated workflow; and
- plugin lifecycle state is managed by the plugin runtime, not transported as
  broker work.

Events are observations of lifecycle points, not commands and not the source
of truth for execution. Tool/provider invocation remains synchronous through
`ExecutionEngine` and `Dispatcher`. Workflow/agent outcomes are returned
directly and may be recorded through `MemoryStore`; event delivery failure is
not used to decide those outcomes.

### Observability and memory relationship

`EventBus`, `StructuredEventSink`, logging, security audit, and `MemoryStore`
are separate mechanisms:

- typed events notify in-process handlers;
- execution emits structured observations with request correlation IDs;
- logs describe runtime behavior;
- authorization audit records security decisions through `AuditSink`; and
- memory optionally records execution/workflow/agent outcome summaries.

None is a durable event log for replay. A distributed transport must not turn
one into another or silently duplicate sensitive payloads across them.

### Existing architectural wording

ADR-0008 and current docstrings anticipated that a future distributed
implementation might satisfy `EventBus` as a drop-in. This is an aspiration,
not proof that the v1.x Protocol fully represents broker semantics. Its
synchronous subscription and swallowed-handler-failure behavior cannot express
acknowledgements, durable consumer identity, redelivery, replay, offsets,
backpressure, or shutdown. A remote implementation could preserve the narrow
surface only by hiding important operational semantics or weakening existing
behavior. Sprint 39 therefore does not approve such an implementation.

## Problem decomposition

Distributed messaging is not one feature:

| Concept | Definition | Demonstrated Kernel need |
|---|---|---|
| In-process event notification | Synchronous callbacks to local subscribers | Already solved by `EventBus` |
| Durable event persistence | Store facts so they survive process failure | Product audit/repository need exists; no Kernel lifecycle-event need |
| Inter-process event delivery | Deliver between processes of one deployment | Consumers use shared databases/HTTP; no Kernel event requirement |
| Cross-service messaging | Communicate between separately deployed services | Product integration concern; no approved Kernel consumer |
| Command queue | Request that a named action be performed later | Not an event; no Kernel requirement |
| Work queue | Competing consumers claim jobs | Product/runtime operations; no Kernel requirement |
| Pub/sub | Fan one publication to multiple consumers | Local form already solved; remote form unproven |
| Event streaming | Ordered retained log with offsets/replay | No consumer evidence |
| Event sourcing | Domain state reconstructed from events | No Kernel or consumer architecture adopts it |

Conflating these would create a contract that promises incompatible delivery,
ownership, and failure semantics.

## Consumer evidence

### Mellivor AI Security

Evidence reviewed includes ADR-0038/0039 durable backend and HA design,
ADR-0040 observability, ADR-0041 SIEM boundary, ADR-0042 deployment isolation,
the roadmap, deployment material, and the implemented SIEM/audit surfaces.

| Requirement | Evidence |
|---|---|
| Multiple processes | Supported conceptually as N stateless Gateway/control-plane instances sharing one durable backend and identical configuration. No cross-instance bus is required. |
| Producer/consumer | Security decisions and audit writes are produced by the product; repositories and pull-based SIEM clients consume stored audit data. Kernel lifecycle events are not the integration unit. |
| Durability | Audit/repository transactions are durable product state. A crash between enforcement and audit commit is explicitly accepted residual risk; closing it would require a product transaction/outbox decision. |
| Ordering | Repository query/cursor behavior, not broker ordering. No global event order is specified. |
| Retry/delivery | SIEM delivery is implemented as a client-pulled JSON export over durable audit data. The SIEM client owns polling/retry. No push transport exists. |
| Semantics | Current export can overlap batches; the downstream consumer must tolerate duplicates. This is not an `EventBus` guarantee. |
| Scale | Multi-instance readiness is discussed, but no event rate, queue depth, lag SLO, partition count, or broker capacity is supplied. |
| Topology | SaaS, Private Cloud, and On-Prem use the same product artifact. On-Prem disallows mandatory unapproved external services. |
| Operational owner | Product/deployment owns database, load balancer, credentials, TLS, backup, retention, SIEM client, and availability. No broker operator exists. |

The accepted SIEM boundary explicitly rejects push delivery, message brokers,
queues, streaming platforms, and a second audit store for the current product.
Mellivor AI Security therefore provides evidence against adding a Kernel
broker abstraction now.

### Mellivor One

Evidence reviewed includes PostgreSQL/database-per-tenant ADRs, automation
architecture, synchronous execution/webhook services, audit storage ADR, the
canonical identity migration ADR, requirements, and deployment guidance.

| Requirement | Evidence |
|---|---|
| Multiple processes | Flask/gunicorn deployment and shared PostgreSQL are real, but no broker worker topology is documented. |
| Producer/consumer | HTTP/webhook requests invoke product automation services synchronously. Product repositories store execution and audit state. No external consumer subscribes to Kernel lifecycle events. |
| Durability | Tenant-local PostgreSQL and Control Plane state are product-owned sources of truth. Identity design includes a bounded transactional outbox concept in the same PostgreSQL transaction as future identity mutations. |
| Ordering | Automation step sequence and repository ordering are product rules. No broker partition/order contract exists. |
| Retry/delivery | Outbound webhook failure is a direct action failure. No durable retry worker, acknowledgement protocol, dead-letter policy, or replay service is approved. |
| Semantics | No at-most/at-least/exactly-once message contract is documented. Product idempotency is operation-specific. |
| Scale | No event throughput, queue growth, worker count, lag target, partition strategy, or retention requirement exists. |
| Topology | Modular monolith with managed PostgreSQL options and database-per-tenant isolation. |
| Operational owner | Mellivor One owns tenant routing, database transactions, webhooks, migrations, credentials, backups, and deployment. No broker owner exists. |

The identity outbox is evidence that PostgreSQL can atomically persist a
product event beside product state. It is not evidence for exporting Kernel
events, a generic message envelope, or a transport backend.

### Other consumers

Kernel names future Mellivor products generically. The minimal sibling CRM
workspace provides no event architecture. No other consumer supplies a
producer/consumer pair, durability/ordering/retry contract, scale, topology,
or operational owner suitable for a Kernel decision.

## Distributed event need

Products have distributed integration needs, but no demonstrated **Kernel**
need. Their durable facts are product audit/domain records whose transaction,
tenant, retention, and authorization boundaries Kernel cannot own. Kernel
lifecycle events remain useful local observations and must not become hidden
commands or authoritative domain records merely because a broker exists.

## Kernel boundary and conceptual primitives

No new primitive is approved:

| Concept | Assessment |
|---|---|
| `EventTransport` | Too vague: could mean fire-and-forget publication, durable log, queue, or RPC. It would import operational semantics without a consumer. |
| `EventPublisher` | `EventBus.publish` already covers local notification. Remote publication needs explicit failure/durability semantics absent from this name. |
| `EventConsumer` | Broker consumers require durable identity, acknowledgement, retry, offsets, concurrency, shutdown, and poison handling. `EventHandler` cannot represent these and no portable subset is proven. |
| `DurableEventSink` | Potentially the smallest future seam for append-only lifecycle export, but payload/schema/transaction/failure requirements are unproven and product audit sinks already exist. |
| `MessageEnvelope` | Existing events have ID/time and subsystem payloads. Correlation, causation, schema, tenant, and trace fields are not uniformly present; guessing them would create a competing event model. |

Message brokers are generic technical infrastructure under ADR-0003 only when
a Kernel contract naturally requires them. ADR-0003 permits such adapters; it
does not mandate a speculative abstraction.

## EventBus relationship

Alternatives:

- **A. Implement existing `EventBus`: rejected for distributed durability.**
  It cannot honestly expose acknowledgements, retries, durable subscriptions,
  replay, backpressure, or shutdown. Blocking remote I/O would alter publisher
  latency/failure expectations; hiding it would obscure delivery loss.
- **B. Bridge existing `EventBus` to external transport: plausible product
  pattern, not approved Kernel surface.** A local handler may explicitly
  serialize selected safe events into a product outbox/transport. The bridge
  must document that local publication and remote delivery are separate
  outcomes and cannot claim atomicity without a shared transaction.
- **C. Separate transport abstraction: only future Kernel candidate.** If
  multiple consumers prove the same transport-neutral semantics, a distinct
  contract avoids reinterpreting v1.x `EventBus`. No shape is justified now.
- **D. Product-owned: selected.** Products choose which events cross process
  boundaries and own persistence, schema, authorization, delivery, and
  operations.
- **E. Other architecture: product database/outbox plus product worker is
  appropriate where transactional durability is required, but it remains
  outside Kernel.

In-process `EventBus` stays deterministic, dependency-free, and lightweight.

## Delivery semantics boundary

- **At-most-once:** can lose messages after publication/failure. May suit
  expendable telemetry, but cannot be a universal Kernel default.
- **At-least-once:** common durable target; implies duplicates and requires
  consumer idempotency. “Published” and “processed” remain distinct.
- **Exactly-once:** not promised. Brokers, databases, external side effects,
  retries, and consumer crashes prevent a universal end-to-end guarantee.
  Transactional broker features do not make arbitrary tool/product effects
  exactly once.
- **Ordering:** can be defined only within a partition/key/stream, not globally
  across services. Existing local subscription order must not be extrapolated.
- **Acknowledgements/retries/dead letters/replay:** transport/adapter mechanics
  whose policy, retention, attempt limits, and operator actions belong to the
  product/deployment.
- **Idempotency:** consuming operation responsibility, supported by stable
  message/event IDs and product-owned deduplication state where required.
- **Poison messages:** must be quarantined or dead-lettered after bounded
  attempts; never retried infinitely or logged with sensitive payloads.

A future Kernel contract, if justified, should state the weakest honest
semantics and require adapters to document stronger ones. Products choose
business retry, idempotency, ordering keys, replay windows, and dead-letter
disposition. Deployment configures partitions, retention, acknowledgement
timeouts, and capacity.

## Message envelope decision

No generic distributed envelope is approved. Existing `Event` supplies an ID
and timestamp. Concrete lifecycle events supply subsystem-specific fields;
execution observations separately carry correlation context.

A future transport envelope might need event type, schema version, correlation
and causation IDs, safe payload, and trace propagation, but each requires
evidence and privacy rules. Tenant context must be an explicitly validated
routing attribute supplied by the authorized product boundary, never inferred
from arbitrary payload metadata. Credentials, authorization tokens, connection
details, raw prompts/responses, tool arguments, and product authorization
policy must never be envelope fields.

Adding these fields to the frozen `Event` base would be breaking and is not
necessary. If a future seam is approved, adapter-owned serialization metadata
should wrap—not mutate—the existing event.

## Serialization decision

Serialization is not part of `EventBus` and no shared serializer is approved.

- Never pickle arbitrary Python objects for remote transport.
- A product/adapter must define an allowlisted event type registry and explicit
  encoding, normally JSON-compatible primitives with UTC timestamp and stable
  identifier representation.
- Schema versions must be explicit at the transport boundary. Consumers must
  define unknown-field and unknown-type handling; schema changes must remain
  backward compatible for the supported retention/replay window.
- Dataclass conversion alone is not a security/schema policy. Nested payloads,
  enums, datetimes, arbitrary metadata, and sensitive strings require explicit
  projection and validation.
- Deserialization produces untrusted data, not a trusted in-process event or
  execution request.

Whether a reusable codec eventually belongs in Kernel or one adapter cannot be
decided before two real event families prove the same wire contract.

## Security and authorization boundary

- Broker/service credentials, TLS, certificates, endpoint trust, network
  policy, encryption at rest, key rotation, and access control belong to the
  deployment and must be dependency-injected/redacted.
- Publication must project the minimum safe payload. Existing lifecycle events
  were designed for local use and are not automatically safe for external
  distribution.
- Tenant routing must be established by an authenticated product boundary.
  Topic, partition, queue, header, or payload tenant values are not proof of
  identity or authorization.
- A received message is untrusted input and conveys no authority. Any requested
  tool/provider/product operation must be reconstructed through validated
  product logic and the existing Kernel authorization/dispatch path.
- Consumers must defend against spoofing, replay, duplicates, stale schemas,
  cross-tenant routing, decompression/payload bombs, and poisoned content.
- Logs/metrics may include safe IDs, event type, attempts, lag, and outcome;
  they must redact payloads, headers, credentials, connection strings, and
  broker diagnostics that contain data.
- Backup/retention/legal deletion and replay authorization remain product and
  deployment responsibilities.

Kernel must not add RBAC or broker authentication through this work.

## Failure and backpressure boundary

Broker unavailability, slow consumers, queue growth, retries, dead letters,
partial publication, shutdown, cancellation, and bounded buffers are real
distributed-runtime concerns. Hiding them behind `publish(event) -> None`
would be unsafe.

Kernel should not create background workers or own these policies now. A future
narrow transport might expose explicit synchronous append acceptance/failure
only; consumer processes, acknowledgement, retry schedules, backpressure,
draining, cancellation, and operational health would remain adapter/product
runtime concerns. Any in-process bridge must use bounded resources and define
what happens when full; silent unbounded buffering is prohibited.

Transactional state change plus publication has a dual-write failure window.
Where this matters, a product-owned outbox committed with product state is the
honest pattern. Kernel cannot make an unrelated product database and broker
atomic.

## Candidate technology evaluation

Only PostgreSQL outbox has repository evidence, and only as a product pattern:

| Candidate | Evidence and decision |
|---|---|
| PostgreSQL outbox | Mellivor One already owns PostgreSQL transactions and its identity design names an outbox. Fits Private Cloud/On-Prem and deterministic database tests. It still requires product schema, dispatcher/worker, retention, locking, retries, and destination. Not selected as Kernel infrastructure. |
| Redis Streams | No deployed Redis, stream consumer, operator, retention, or dependency evidence. Not selected. |
| RabbitMQ | No deployment, queue topology, operator, or consumer evidence. Not selected. |
| NATS | Mentioned only historically as a generic future example. No deployment evidence. Not selected. |
| Kafka | Mentioned only historically as a generic future example. Operational weight and semantics are unsupported by current evidence. Not selected. |

Mellivor AI Security's current SQLite/single-writer and pull-SIEM architecture
and both products' Private Cloud/On-Prem concerns argue against a mandatory new
service. Selected technology: **none**.

## Observability relationship

Distributed delivery would need safe propagation of existing correlation IDs
where available, plus new transport-level observations such as publish
acceptance/failure, consumer lag, attempts, dead-letter count, and processing
latency. These are adapter/product metrics, not new business events.

Trace context must be allowlisted and treated as correlation, never authority.
Remote spans must not include message payloads. Existing
`StructuredEventSink`, logs, metrics Protocols, and no-op defaults remain
vendor-neutral and unchanged. No telemetry SDK or broker-specific exporter is
justified.

## Compatibility and SemVer

Sprint 39 changes no code or public API. `Event`, `EventHandler`, `EventBus`,
`EventRegistration`, `InMemoryEventBus`, `ExecutionEngine`, `Dispatcher`,
workflow, tools/plugins, authorization, memory, and observability contracts
remain unchanged.

The selected product-owned approach requires no Kernel version change. If a
future Kernel transport is proven, a separate module and Protocol could be an
additive v1.x capability so long as existing events/bus/publishers remain
untouched. Adding required fields to `Event`, changing `publish` to async or to
return acknowledgements, changing handler error propagation, widening exact-
type subscription, or altering execution to depend on remote delivery would be
breaking. Such changes are neither necessary nor recommended, so a major
version is not required.

## Risks and open questions

The main risk is that product teams may build different delivery mechanisms.
That variation is currently correct because their sources of truth,
transactions, tenants, consumers, and failure policies differ. Shared code
should be extracted only after repeated use proves a common seam.

Questions required to reopen Kernel-level design:

1. Which named Kernel event must cross a process boundary, and why is a product
   audit/domain record insufficient?
2. Who produces and consumes it, in which processes/services?
3. Is publication observation, durable fact, command, or work request?
4. What are durability, ordering key, delivery, acknowledgement, retry,
   idempotency, replay, retention, and dead-letter requirements?
5. What event rate, payload size, queue depth, lag SLO, and outage window apply?
6. Which transaction establishes the event and how is dual-write avoided?
7. How are tenant routing, authorization, schema compatibility, redaction, and
   deletion handled?
8. Which deployment already operates the candidate technology, and who owns
   upgrades, credentials, backups, monitoring, and incidents?
9. Do at least two consumers demonstrate the same transport-neutral contract?

## Outcome

- Decision: **D — product/deployment responsibility**.
- Proposed primitives/modules: **none**.
- Selected technology: **none**.
- Implementation ADR: **not justified**.
- Public API and v1.x compatibility: **unchanged**.
- Dependencies, version, code, UI, workers, queues, and daemons: **unchanged**.
- Next action: keep local lifecycle events local; require a concrete producer/
  consumer and operational evidence before reopening a Kernel transport seam.
