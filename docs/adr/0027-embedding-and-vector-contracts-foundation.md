# 0027. Embedding and vector contracts foundation

Status: Proposed
Date: 2026-09-02

## Context

Sprint 34's
[Architecture Challenge](../reviews/sprint34-embeddings-vector-store-architecture-challenge.md)
asked whether generic embedding generation and vector persistence/search
belong in Mellivor Kernel. The Product Owner accepted its decision
**B — APPROVE PARTIALLY**:

- Kernel may own separate, independently configurable embedding and vector
  infrastructure contracts;
- embeddings must not extend the frozen `BaseProvider` contract;
- vector search must not extend or reinterpret the frozen `MemoryStore`
  contract; and
- RAG, ingestion/chunking policy, authorization, ranking, prompt/context
  construction, citations, answer generation, and UI remain outside Kernel.

ADR-0002 already names model-provider and memory abstractions as Kernel
responsibilities. ADR-0003 explicitly identifies model providers and vector
stores as generic infrastructure that may be integrated here. ADR-0019 kept
embeddings/vector/RAG in Future Research because the contract boundary was
unresolved. Sprint 34 resolved the ownership boundary but deliberately left
six contract questions for this ADR: model selection, protocol subset,
similarity metric, metadata portability, public-export timing, and the second
backend gate.

This ADR defines an implementation-ready design but authorizes no code. It
remains `Proposed` until Product Owner approval. No public API, dependency,
roadmap schedule, or release scope changes while it is Proposed.

## Decision

Introduce two independent foundations after this ADR is accepted:

1. an embedding foundation associated with model-provider infrastructure;
2. a vector-store foundation associated with memory infrastructure.

Neither foundation imports or owns the other. Products explicitly compose an
`EmbeddingResult` into `VectorRecord` values and verify that result/store
dimensions agree. Kernel supplies no automatic embedding-to-store pipeline.

The proposed final public types are exactly:

- `EmbeddingProvider`
- `EmbeddingRequest`
- `EmbeddingResult`
- `EmbeddingError`
- `VectorRecord`
- `VectorMatch`
- `VectorStore`
- `VectorStoreError`

No registry, factory, filter language, pagination object, collection manager,
metric enum, ingestion service, or RAG type is included.

### Placement and dependency direction

The first proof uses internal modules
`mellivor_kernel.providers._embeddings` and
`mellivor_kernel.memory._vector`. The experimental OpenAI-compatible adapter
and in-memory store also remain internal to their respective packages. After
the second-backend gate, the accepted shapes move to public
`mellivor_kernel.providers.embeddings` and
`mellivor_kernel.memory.vector` modules and are re-exported from their package
boundaries.

The embedding module may depend on existing provider health/error concepts but
never on `memory`. The vector module may depend on `core`/`memory` errors but
never on `providers`, `execution`, `workflow`, or `agents`. No existing package
imports either experimental foundation.

## Embedding contract

### `EmbeddingProvider`

The contract is a synchronous, structural `Protocol` independent of
`BaseProvider`:

```python
@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def name(self) -> str: ...

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

    def check_health(self) -> ProviderHealthCheck: ...
```

`name` is a non-blank stable implementation identifier. `embed()` either
returns one complete validated result or raises `EmbeddingError`; it never
returns partial success. `check_health()` is explicit and returns the existing
`ProviderHealthCheck`. Import and construction make no health/network call.
Health checks translate an embedding failure to `healthy=False` rather than
raising it, matching current provider behavior.

The API is synchronous because every current Kernel provider and execution
seam is synchronous. There is no conditional awaitable, background worker, or
hidden thread. Once a synchronous call begins, the shared contract offers no
cooperative cancellation. A caller running it in another thread may abandon
its wait, but that does not guarantee cancellation of the underlying request.
Bounded adapter timeouts remain the termination mechanism. A future async
contract, if demonstrated, must be separate and additive.

The Protocol makes no thread-safety guarantee. Each implementation documents
whether its client can be shared. Callers must synchronize access or create
separate instances when an implementation does not explicitly promise safe
concurrent use.

### Model selection and configuration

**Decision: A — provider-instance configuration only.**

`EmbeddingRequest` has no model override. One provider instance uses one
configured model, keeping model identity and vector dimensions stable and
making accidental mixed-model storage harder. Callers needing another model
construct another provider instance.

The Protocol does not prescribe a constructor. Concrete adapters may consume
the existing `ProviderConfiguration` unchanged where its `provider_name`,
`default_model`, `api_key`, `base_url`, `timeout_seconds`, `max_retries`, and
`extra` fields fit. `default_model` is required by the first adapter. No field
is added to `ProviderConfiguration`.

Timeout and bounded retry behavior are owned by each concrete adapter and its
configuration. An adapter must translate its final failure to
`EmbeddingError`; it must not retry validation, authentication, or malformed
response failures. Optional SDK/transport dependencies belong to adapter
extras and never become base dependencies.

### `EmbeddingRequest`

Exact shape:

```python
@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
```

Invariants:

- `texts` is a non-empty tuple;
- every item is a non-blank `str`;
- duplicates are valid and produce distinct results at their positions;
- order is binding; and
- construction performs no normalization, truncation, batching, tokenization,
  or network access.

A single input is represented by a one-element tuple. Empty batches are
invalid and raise `EmbeddingError` at construction.

No model override, metadata, purpose/input-type, dimensions override, task
hint, encoding format, or provider options are included. Those fields do not
have stable semantics across plausible OpenAI-compatible, Gemini, and local
embedding implementations. Vendor-specific request options may be fixed in a
concrete adapter's configuration only when they do not change this contract.

### `EmbeddingResult`

Exact shape:

```python
@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    model: str
    dimensions: int
```

Invariants:

- `vectors` is non-empty;
- the provider returns exactly one vector per request text;
- vector position exactly matches input position, regardless of backend
  response order;
- `model` is non-blank and identifies the model actually used;
- `dimensions` is a positive integer;
- every vector length equals `dimensions`;
- every component is a real number other than `bool`, normalized to `float`,
  and finite (`NaN` and positive/negative infinity are invalid); and
- vectors are not magnitude-normalized by Kernel.

The value object can validate its intrinsic shape; the adapter additionally
validates result count against the originating request and model identity
against its configuration.

Usage, tokens, cost, latency, request IDs, and arbitrary metadata are excluded.
Current repository evidence provides no portable cross-provider requirement or
meaning for them. They may be introduced only through a later additive design
with a demonstrated consumer.

### `EmbeddingError`

`EmbeddingError` is the one shared embedding failure type and subclasses
`ProviderError`. It covers:

- invalid request/result values;
- unavailable or misconfigured embedding service after construction;
- authentication rejection;
- timeout or transport failure after bounded retries;
- malformed backend responses;
- result-count/model/dimension mismatch; and
- non-numeric or non-finite vector components.

One shared type is sufficient initially. Generic callers can fail, report, or
retry according to their own policy without coupling to one vendor's error
taxonomy. Concrete adapter modules may define narrower subclasses for callers
that explicitly depend on that adapter, but those subclasses are not part of
the shared eight-type contract.

Invalid `ProviderConfiguration` construction continues to raise the existing
`ProviderConfigurationError`; an adapter-specific missing model/endpoint
condition discovered by its constructor is translated consistently with
existing provider convention. `check_health()` reports failure rather than
raising `EmbeddingError`.

Messages must not contain source text, vectors, credentials, authorization
headers, endpoint user information, response bodies, connection strings, or
raw vendor diagnostics. Raw exceptions may be chained as causes for debugging
but are not exposed through the stable message contract.

## Vector-store contract

### Similarity metric

**Decision: cosine similarity is the sole initial shared metric.**

Supporting multiple metrics would require a public enum/configuration surface
before a consumer has demonstrated it. Implementation-defined scores would be
ambiguous. Every conforming store therefore evaluates cosine similarity:

```text
cosine(a, b) = dot(a, b) / (norm(a) * norm(b))
```

Record and query vectors must have non-zero magnitude. Scores are finite
floats in the inclusive range `[-1.0, 1.0]`; implementations clamp only
floating-point round-off beyond those mathematical bounds. Higher scores mean
greater similarity. Query results order by descending score, then ascending
record ID for exact score ties. Scores are meaningful within this defined
metric but still should not be treated as calibrated relevance probabilities.

The metric is fixed by the contract, not selected per request or exposed as a
public configuration field. A future metric requires a separate additive
contract/versioned capability rather than reinterpreting `score`.

### `VectorRecord`

Exact shape:

```python
@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: str
    vector: tuple[float, ...]
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
```

Invariants:

- `id` is caller-owned, non-blank, and stable;
- `vector` is non-empty, contains only finite real values other than `bool`,
  is normalized to floats, and has non-zero magnitude;
- the store validates vector length against its configured `dimensions`;
- metadata keys are non-blank strings;
- metadata values are JSON scalars only: `str`, `int`, finite `float`, `bool`,
  or `None`; and
- metadata is defensively copied into a read-only mapping during construction,
  so mutation of the caller's input cannot mutate the record.

Nested objects and arrays are excluded. Scalar JSON metadata is portable
across in-memory, PostgreSQL/pgvector, Qdrant, Pinecone-like, and local-store
adapters without an unconstrained Python-object serialization contract.
Metadata is opaque payload in v1: no filtering semantics are defined.

Namespace and tenant identity are not record fields. The same caller-owned ID
may exist independently in different operation namespaces.

### `VectorMatch`

Exact shape:

```python
@dataclass(frozen=True, slots=True)
class VectorMatch:
    id: str
    score: float
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
```

`id` and metadata identify the matched record; `score` obeys the cosine
semantics above. Metadata is also a defensive read-only snapshot. The stored
vector is deliberately omitted to minimize sensitive-data exposure and
payload size. A caller requiring vectors uses `fetch()` explicitly. There is
no product rank, explanation, citation, source text, or reranking metadata.

### Namespace model

Namespace is a mandatory keyword-only argument on every store operation. It
is never empty and matches this portable representation:

```text
[A-Za-z0-9][A-Za-z0-9._-]{0,127}
```

It is a caller-selected storage routing/isolation key. No default/global
namespace and no pre-bound namespace mode are part of the first contract.
Callers may build their own pre-bound wrapper without expanding Kernel.

Namespace is not authentication, authorization, RBAC, tenant verification, or
proof of physical isolation. Products authorize a subject and map it to a
namespace or separate store before invoking Kernel. A backend must never
silently search or mutate another namespace.

### `VectorStore`

Exact structural contract:

```python
@runtime_checkable
class VectorStore(Protocol):
    @property
    def dimensions(self) -> int: ...

    def upsert(self, records: tuple[VectorRecord, ...], *, namespace: str) -> None: ...

    def query(
        self, vector: tuple[float, ...], *, namespace: str, limit: int
    ) -> tuple[VectorMatch, ...]: ...

    def fetch(self, record_ids: tuple[str, ...], *, namespace: str) -> tuple[VectorRecord, ...]: ...

    def delete(self, record_ids: tuple[str, ...], *, namespace: str) -> None: ...
```

`dimensions` is a positive, immutable per-instance value. Construction and
backend configuration are implementation-specific; the Protocol prescribes no
constructor, endpoint, credential, index, collection, or schema API.

Operation semantics:

- `upsert()` requires a non-empty tuple. Duplicate IDs in one batch are
  invalid and reject the whole call before backend mutation. A record replaces
  the same ID within the same namespace; it never affects another namespace.
- `query()` requires a finite, non-zero vector matching `dimensions` and a
  positive integer `limit` (with `bool` rejected). It returns at most `limit`
  matches in deterministic score/ID order. No match returns an empty tuple.
- `fetch()` preserves requested ID order and omits missing IDs. Duplicate
  requested IDs are invalid. An empty tuple returns an empty tuple without
  backend access.
- `delete()` is idempotent for missing IDs and returns `None`, avoiding a
  removal-count guarantee that many remote stores cannot supply. Duplicate IDs
  are invalid. An empty tuple is a successful no-op without backend access.
- All values and the complete batch are validated before backend access where
  possible. Validation failure never partially mutates the store.
- Upsert/delete are retry-safe because their final state is idempotent. The
  shared contract does not promise cross-record transaction atomicity after a
  backend failure; implementations document consistency and callers reconcile
  an indeterminate remote batch by retrying or fetching.

The Protocol has no thread-safety guarantee. Implementations document their
concurrency behavior; callers synchronize when no guarantee is made. It owns
no global connection, worker, indexer, background task, or lifecycle beyond
resources explicitly constructed by the caller.

No pagination, filtering DSL, hybrid search, collection administration,
schema/index migration, backend-specific search parameters, or RAG operation
is present.

### `VectorStoreError`

`VectorStoreError` subclasses `MemoryError` and is the sole shared failure
boundary for invalid records/queries/namespaces, dimension or metric-invalid
vectors, unavailable backends, credentials rejected by a backend, timeout or
transport/storage failures, malformed backend results, and violated ordering
or score invariants.

Missing IDs and empty query results are normal outcomes, never errors. Error
messages follow the security rules below. Concrete adapters may define
module-specific subclasses without expanding the shared contract.

After a successful `delete()`, records are deleted from the backend's logical
namespace according to its documented consistency model. The shared contract
does not promise physical erasure from replicas, snapshots, backups, logs, or
vendor retention systems.

## First proof implementations

### `InMemoryVectorStore`

The first vector-store proof is dependency-free, process-local, and explicitly
non-production:

- dictionaries partition records first by namespace and then ID;
- search computes exact cosine similarity over every record in the namespace;
- results sort by descending score and ascending ID on exact ties;
- all caller inputs and returned metadata are snapshots;
- deletion and upsert are immediately visible;
- state is not persistent, distributed, indexed, encrypted, or thread-safe;
- no approximate-nearest-neighbor algorithm or scalability claim is made.

It proves contract determinism, validation, isolation, and composition. It does
not dictate external-store indexing, persistence, consistency, or lifecycle.

### `OpenAICompatibleEmbeddingProvider`

The first embedding proof is an optional direct-HTTP adapter, not an
`openai`-SDK adapter. This remains the smallest portable choice because
`LocalProvider` has already proven injected HTTPX transport, explicit endpoint
ownership, redirect/proxy controls, bounded retries, and deterministic mocks.

The adapter uses a new optional `embeddings` extra that directly owns the
supported HTTPX range; base dependencies remain empty. It accepts existing
`ProviderConfiguration`, requires explicit `base_url` and `default_model`,
uses optional Bearer `api_key`, appends `/embeddings`, disables redirects and
environment-proxy inheritance on its owned client, and makes no import-time or
constructor-time request.

The only request subset is:

```json
{"model": "<configured model>", "input": ["<text>", "..."]}
```

The only response subset required is an object containing non-blank `model`
and `data`, where `data` contains exactly one object per input with a unique
zero-based `index` and numeric `embedding` array. Response entries may arrive
out of order; the adapter reorders them by `index` and rejects missing,
duplicate, or out-of-range indices. Usage and all other response fields are
ignored. The adapter does not send provider-specific dimensions, purpose,
encoding, or user fields.

Health checking explicitly embeds one fixed synthetic probe only when called.
Timeout/transport retries are bounded by `max_retries`; validation,
authentication, HTTP status, and malformed responses are not retried.

The supported claim is only “OpenAI-compatible embeddings endpoint implementing
the documented subset.” No Ollama, LM Studio, vLLM, OpenAI service, local
runtime, or model-build compatibility is claimed without separate real
validation. Kernel never installs/starts a runtime or downloads a model.

## Public export and second-backend gate

**Decision: C — internal/experimental until a second backend proves the
abstraction.**

The first implementation sprint places experimental contracts behind internal
modules and does not add the eight names to `providers.__all__` or
`memory.__all__`. Its specification must label them experimental and outside
the v1.x compatibility promise. This gives the first adapter/reference store
and an end-to-end synthetic consumer room to expose mistakes without freezing
them.

A second, genuinely external `VectorStore` implementation selected from
consumer deployment evidence is required **before package-level public export
or a v1.x release that advertises the contracts**. That implementation must
demonstrate dimensions, namespaces, scalar metadata, cosine score conversion,
deterministic ordering, fetch/delete behavior, translated failures, and its
consistency/lifecycle documentation.

After that gate, a follow-up acceptance/export decision may expose the exact
eight types from `mellivor_kernel.providers` and `mellivor_kernel.memory` as an
additive MINOR change. Concrete adapters remain explicit module imports so
their optional dependencies do not affect package import.

No external backend is selected here. pgvector, Qdrant, Pinecone-like
services, and SQLite vector extensions are examples only. The consuming
product's approved deployment, operational, and security requirements select
the proof backend.

Standard-library SQLite is not an acceptable production vector proof: it has
no native vector type, distance operator, or approximate index. A Python scan
over serialized vectors would misrepresent its production semantics. A named
SQLite vector extension may be evaluated later as an optional external
dependency and must remain separate from `SQLiteMemoryStore`.

## Security boundaries

Every implementation must guarantee:

- source texts, vectors, metadata, queries, matches, credentials,
  authorization headers, connection strings, and response bodies are not
  logged by default or included in repr/error text;
- raw vendor/database exceptions are translated to the appropriate Kernel
  boundary before propagation;
- credentials and endpoints are explicit caller configuration, with no hidden
  environment credential or cloud fallback;
- import/construction performs no hidden network access;
- endpoint trust and egress/SSRF policy belong to the caller/deployment;
- namespace is routing only, never authentication or authorization;
- no product tenant ID is inferred from metadata;
- delete behavior and backend consistency are documented without claiming
  physical erasure of replicas/backups; and
- no runtime, database, model, process, background worker, or index lifecycle
  is implicitly installed, started, or managed.

Products remain responsible for authentication, RBAC, tenant-to-namespace
mapping, data classification, encryption, network policy, retention, legal
erasure, backups, residency, and backend operation. This ADR adds none of
those product policies to Kernel.

## RAG boundary and non-goals

This decision does not approve RAG. Kernel will not define or implement:

- document/corpus ownership or ingestion;
- loaders, parsers, chunking, batching policy, or ingestion schedules;
- document authorization or tenant policy;
- metadata filtering, product ranking/reranking, or relevance thresholds;
- context-window or prompt assembly;
- citations, grounding, or answer generation;
- UI or knowledge-management screens;
- an automatic embedding/store/generation pipeline; or
- `RAGEngine`, `Retriever`, `KnowledgeBase`, or equivalent framework types.

Reusable ingestion utilities may later belong in a separately approved shared
library if multiple products prove common requirements. Product behavior stays
in consuming products. Existing tools/workflows can compose product-owned
behavior without modifying Kernel contracts.

## Compatibility

Implementation is additive within v1.x and must not modify or reinterpret:

- `BaseProvider` or its constructor/abstract members;
- `ProviderCapabilities` or `supports_embeddings`;
- `ProviderConfiguration`;
- `MemoryStore`, `MemoryEntry`, `MemoryQuery`, or `MemoryResult`;
- `WorkflowStep`, `WorkflowDefinition`, or workflow options;
- `ExecutionTarget`, `Dispatcher`, or execution behavior; or
- any other frozen v1.x public contract.

The foundations create no dependency between `memory` and `providers` and add
no mandatory package dependency. Experimental implementation changes no public
API. Later package exports of new types are additive MINOR changes under
ADR-0005. No MAJOR release is required.

Adding an abstract method to `BaseProvider`, changing text-memory search to
semantic ranking, adding fields to frozen public dataclasses, adding an
execution target, or making a vector/embedding dependency mandatory is not
authorized and would require a new compatibility decision.

## Alternatives considered

- **Extend `BaseProvider`.** Rejected as unrelated capability coupling and a
  breaking abstract-contract change.
- **Use `BaseProvider.invoke()` for embeddings.** Rejected because generic
  mappings cannot express one-to-one ordering, dimensions, and finite numeric
  invariants safely.
- **Make `VectorStore` a `MemoryStore`.** Rejected because ranked numeric
  similarity is not the text filter/search contract frozen by ADR-0009.
- **Per-request model selection.** Rejected initially; one model per provider
  instance is smaller and dimensionally safer.
- **Purpose, metadata, usage, and vendor option fields on embedding values.**
  Rejected as speculative and non-portable.
- **Implementation-defined or configurable metrics.** Rejected because score
  meaning would be ambiguous; cosine is widely supported and exact.
- **Opaque Python metadata or nested arbitrary JSON.** Rejected because it
  weakens backend portability and immutability. Scalar JSON values are enough
  for the first contract.
- **Return vectors in `VectorMatch`.** Rejected to reduce payload and sensitive
  data exposure; explicit `fetch()` is available.
- **Default/pre-bound namespace.** Rejected because explicit per-operation
  routing prevents hidden global state and keeps the isolation boundary
  visible.
- **Public export after one in-memory backend.** Rejected under the dogfood
  principle: an external store must prove that the contract is not an
  in-memory model disguised as an abstraction.
- **Require an external backend choice now.** Rejected because no consuming
  deployment evidence selects one.

## Open questions

No contract-level question remains open for the experimental foundation.
Sprint 34's questions are resolved as follows:

1. model selection is provider-instance-only;
2. the first adapter's exact request/response subset is fixed above;
3. cosine similarity is fixed with `[-1, 1]`, higher-is-better scores and ID
   tie-breaking;
4. metadata is immutable scalar JSON only;
5. a second external vector backend is required before public export; and
6. backend technology remains intentionally unselected until consumer
   deployment evidence exists.

The sixth item is a future implementation selection gate, not an ambiguity in
the shared contract.

## Consequences

- Embeddings and vector search gain precise, independent seams without
  contaminating frozen generation or text-memory contracts.
- The first implementation can be tested end to end without creating a v1.x
  compatibility promise prematurely.
- Cosine-only semantics and scalar metadata reduce initial breadth but make
  ordering, scores, validation, and portability unambiguous.
- Callers construct one embedding provider per model and explicitly compose
  it with a dimension-compatible store.
- External stores must normalize their native response into deterministic
  cosine semantics, which may require adapter-side sorting or score
  conversion.
- No production vector backend is promised until consumer evidence selects
  and validates one.
- RAG and all business/product policy remain outside Kernel.
- This ADR remains Proposed and authorizes no implementation until Product
  Owner approval changes its status to Accepted.
