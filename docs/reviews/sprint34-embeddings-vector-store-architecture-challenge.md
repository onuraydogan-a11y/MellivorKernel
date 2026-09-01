# Sprint 34 Architecture Challenge: Embeddings and Vector Store

Date: 2026-09-01

Status: Architecture Challenge complete; Product Owner decision pending

Release baseline: `v1.2.0` (`4f8eaf2`)

## Question and decision

Should Mellivor Kernel provide generic embeddings and vector-store
abstractions, and if so, where is the boundary?

**Decision: B — APPROVE PARTIALLY.** Kernel should own two small, independent,
business-agnostic infrastructure contracts:

1. an embedding-generation contract; and
2. a vector persistence/search contract.

Kernel should not own RAG, document ingestion, corpus policy, authorization,
tenant policy, ranking strategy, context construction, prompts, citations, or
answer generation. No implementation is authorized by this challenge. A
Proposed ADR must fix the exact contract before an implementation sprint is
scheduled.

This is a partial approval because the reusable primitives fit existing
Kernel responsibilities, while the larger feature commonly called “RAG” does
not. The challenge also deliberately declines to select a production vector
database without evidence from a consuming deployment.

## Existing architecture audit

ADR-0002 names memory abstraction and multi-model provider abstraction as
Kernel responsibilities. ADR-0003 explicitly identifies model providers and
vector stores as generic infrastructure whose integrations may belong here,
while excluding product data, tenant configuration, business SaaS, and UI.
ADR-0019 nevertheless kept embeddings, vector search, and RAG in Future
Research because their contracts and boundaries were unresolved. This
challenge supplies the missing boundary analysis; it does not itself schedule
the work.

The current `memory` contract is text storage:

- `MemoryEntry` owns text, tags, metadata, and a caller-selected ID;
- `MemoryQuery` performs exact/substring filtering;
- `MemoryStore.search()` returns unranked `MemoryEntry` values; and
- `ExecutionEngine` optionally records outcomes through that contract.

Changing any of those meanings to imply vectors or similarity would violate
ADR-0009 and the v1.x compatibility promise. A vector store is related to the
memory responsibility but is not a `MemoryStore` implementation or subtype.

The current `BaseProvider` contract represents synchronous text-model
invocation through a generic mapping. `ProviderCapabilities.supports_embeddings`
is descriptive metadata only and deliberately has no corresponding method.
Adding an abstract embedding method to `BaseProvider` would break every
provider subclass. Routing embeddings through `invoke()` would avoid a
signature change but would erase the type and dimensional guarantees that
justify having an embedding abstraction at all. Embedding generation must
therefore be a separate contract, even if its concrete infrastructure adapters
live under `providers` and reuse existing configuration/health/error concepts.

Workflow, execution, agents, tools, and plugins do not need modification.
Products can call the new primitives directly or wrap them in tools. A later,
demonstrated orchestration need may add an optional integration above the
contracts, but this challenge does not add an execution target, workflow step
kind, AIEngine method, or plugin capability.

## Consumer need and ownership

Semantic retrieval, knowledge lookup, document similarity, AI-security
context lookup, and future assistant context retrieval all share two technical
operations: convert ordered text inputs to vectors, then persist/search vectors
by stable IDs. Reimplementing those boundaries separately in each product
would create inconsistent provider errors, dimensional validation, ordering,
and backend substitution.

Those shared mechanics do not imply shared product policy.

### Kernel responsibility

- typed, synchronous embedding generation with batch ordering and dimension
  invariants;
- typed vector records and similarity matches;
- a small structurally typed vector-store contract;
- backend-neutral validation and Kernel exception boundaries;
- explicit namespaces as storage-routing scope;
- optional, isolated infrastructure adapters;
- deterministic observable ordering; and
- synthetic, business-agnostic contract and integration tests.

### Shared-library responsibility

Only if multiple products demonstrate the same need, a separate shared
library may own reusable but opinionated ingestion utilities such as document
loaders, format parsing, token-aware chunking implementations, batching
pipelines, or generic reranking helpers. Those facilities compose Kernel
primitives but are not required by the headless runtime itself. They must not
be added here merely because they are reusable Python utilities.

### Product responsibility

- corpus selection, ownership, ingestion schedules, and retention policy;
- document and chunk identifiers beyond the Kernel's format invariants;
- user/tenant authorization and mapping a tenant to a namespace/store;
- metadata schema and which metadata is safe to persist;
- product-specific filters, ranking, reranking, and relevance thresholds;
- prompt/context-window assembly, citations, grounding, and answer policy;
- UI and knowledge-management screens; and
- deployment topology, credentials, backups, encryption, and data residency.

## Embedding abstraction

### Alternatives

**A. Extend `BaseProvider` — rejected.** Embeddings are not text generation.
An added abstract method is breaking; an optional method or use of `invoke()`
would create capability-dependent runtime typing and contaminate a frozen
contract. The existing `supports_embeddings` flag remains descriptive and
must not be reinterpreted as an operation guarantee.

**B. Separate `EmbeddingProvider` contract — selected.** It gives embedding
inputs/results explicit invariants, allows a text-generation provider and an
embedding provider to be configured independently, and permits local or
remote implementations without changing any v1.x type.

**C. Keep embeddings outside Kernel — rejected for the primitive.** ADR-0003
already recognizes model providers as Kernel infrastructure, and multiple
business-agnostic retrieval use cases need the same error and ordering seam.
Embedding-based product behavior remains outside Kernel.

### Proposed minimal contract

The exact spelling remains subject to a Proposed ADR, but the smallest useful
shape is conceptually:

```python
class EmbeddingProvider(Protocol):
    @property
    def name(self) -> str: ...

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

    def check_health(self) -> ProviderHealthCheck: ...


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    model: str
    dimensions: int
```

`EmbeddingError`, derived from `ProviderError`, is the generic boundary for
embedding validation or backend failures. Concrete adapters may add the
established authentication/timeout/connection/response subclasses.

The contract is batch-first: a single input is a one-element tuple. Empty
batches and blank text are invalid. Results preserve input order exactly,
contain one vector per input, and require every vector to have the reported,
positive dimension with finite numeric values. The contract does not normalize
vector magnitude; normalization changes metric semantics and belongs to the
selected model/backend.

The first contract is synchronous, matching every current Kernel provider and
execution seam. An independent async contract could be added later if proven;
returning an awaitable conditionally is rejected. Timeout and retry semantics
belong to concrete adapter configuration and boundary errors, not to the
result value.

Model selection belongs to construction/configuration of an embedding-provider
instance. Existing `ProviderConfiguration` can be reused by adapters where its
fields fit without modification; the generic Protocol does not require that
specific constructor. Fixing one model per instance keeps dimensions stable
and avoids speculative per-request switching. Result model identity is
reported so callers can detect incorrect wiring.

Usage metadata is omitted initially. Token accounting differs by provider and
is not necessary to generate or store vectors. It may be added only when a
real consumer proves a portable shape; a generic mapping would expose surface
without semantics.

## Vector-store abstraction

A vector store belongs alongside memory infrastructure but requires a separate
contract. `MemoryStore` promises text records and unranked filters; a
`VectorStore` promises dimensioned numeric records and ranked similarity.
Neither should subtype or silently adapt the other.

The candidate minimum is:

```python
@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: str
    vector: tuple[float, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorMatch:
    record: VectorRecord
    score: float


@runtime_checkable
class VectorStore(Protocol):
    @property
    def dimensions(self) -> int: ...

    def upsert(self, records: tuple[VectorRecord, ...], *, namespace: str) -> None: ...

    def query(
        self, vector: tuple[float, ...], *, namespace: str, limit: int
    ) -> tuple[VectorMatch, ...]: ...

    def fetch(self, record_ids: tuple[str, ...], *, namespace: str) -> tuple[VectorRecord, ...]: ...

    def delete(self, record_ids: tuple[str, ...], *, namespace: str) -> int: ...
```

`VectorStoreError`, derived from `KernelError`, is the translated failure
boundary. The exact collection types should be confirmed through real adapter
work, but immutable tuples are the default because they match existing Kernel
value objects and make ordering explicit.

IDs are caller-owned, stable keys. Upsert replaces the same ID only within the
same namespace. Every operation requires a non-blank namespace; there is no
implicit global/default collection. Namespace is a storage isolation key, not
an authorization decision.

The store has one positive configured dimension. It rejects records and
queries of another dimension before backend invocation where possible. The
similarity metric is store construction/backend configuration, not a per-query
portable enum: backends support materially different metrics and indexing
parameters. A `VectorMatch.score` must mean “higher is a stronger match,” but
no universal range or cross-store comparability is promised. Results sort by
descending score with stable ID ordering for exact ties.

Metadata is opaque retrieval payload in the first contract. A generic filter
language, pagination/cursors, collection administration, index creation,
hybrid keyword/vector search, and backend-specific search parameters are
omitted. Adding a weak lowest-common-denominator filter would invite callers to
treat it as an authorization boundary. Products needing secure filtered
retrieval must use an appropriately isolated namespace/store or a future
explicitly designed capability.

`fetch()` preserves requested ID order while omitting missing IDs. `delete()`
returns the number removed and is idempotent for missing IDs. A successful
delete guarantees the records are no longer fetchable or searchable through
that logical store; physical erasure from snapshots, replicas, or backups is a
backend/deployment guarantee and must be documented by the implementation.

## Embedding/store separation and portability

`EmbeddingProvider` and `VectorStore` must remain independent. Kernel must not
assume one vendor, credential, model, lifecycle, or deployment supplies both.
The caller explicitly composes generation and storage and verifies that the
embedding result dimension equals the store dimension.

This supports, without changing either contract:

- an OpenAI-compatible embedding endpoint with PostgreSQL/pgvector;
- Gemini embeddings with an external vector database;
- a local embedding model with a SQLite vector extension;
- a local embedding model with Qdrant; and
- a cloud embedding service with Pinecone.

These are portability examples, not selected or certified integrations.

## RAG boundary

This challenge does not approve RAG as a Kernel capability. Kernel primitives
may generate vectors and store/search them. They do not decide what becomes a
document, how it is chunked, when it is embedded, who may retrieve it, how
results are reranked, how many results enter a model context, how prompts or
citations are assembled, or how an answer is generated.

There is intentionally no `RAGEngine`, `KnowledgeBase`, `DocumentIngestor`,
`Retriever`, prompt builder, citation model, or automatic
embedding-to-generation pipeline in the proposed public surface. A product or
separately approved shared library composes those policies. Kernel workflows
and tools are already sufficient for products to orchestrate such behavior
without teaching Kernel what RAG means.

## Security and multi-tenancy boundary

- Vector and embedding data can reveal sensitive source information. Kernel
  contracts and adapters must not log source texts, vectors, metadata,
  queries, result payloads, credentials, or raw vendor errors by default.
- Credentials are explicit caller configuration and may be obtained through
  the existing `SecretProvider`; the new contracts do not embed secret lookup
  or retain resolved secrets in reprs/diagnostics.
- Namespace is mandatory and must be honored exactly by every backend, but it
  is not RBAC, authentication, or proof of tenant isolation. The product
  authorizes the subject and maps it to a namespace or physically separate
  store before calling Kernel.
- Kernel must never inject or trust a tenant identifier from unvalidated
  metadata. Metadata filtering is not an access-control substitute.
- Adapters translate vendor/database exceptions and redact connection strings,
  authorization headers, tokens, query content, and result content.
- Callers own encryption, network policy, backups, retention, legal erasure,
  data residency, and backend lifecycle. Implementations document their
  persistence, consistency, concurrency, and physical-deletion limitations.
- No global client, implicit default endpoint, background indexer, ingestion
  worker, or hidden network call belongs in the contract.

## Proposed public surface and placement

| Type | Purpose | Required? | Likely module | Compatibility risk |
|---|---|---:|---|---|
| `EmbeddingProvider` | Structural embedding-generation seam | Yes | `mellivor_kernel.providers.embeddings` | Low if purely additive |
| `EmbeddingRequest` | Ordered, validated text batch | Yes | `mellivor_kernel.providers.embeddings` | Medium: frozen field shape must be proven before release |
| `EmbeddingResult` | Ordered vectors plus model/dimension identity | Yes | `mellivor_kernel.providers.embeddings` | Medium: avoid speculative metadata |
| `EmbeddingError` | Backend-neutral translated failure | Yes | `mellivor_kernel.providers.embeddings` or provider exceptions | Low |
| `VectorRecord` | Caller-ID vector plus opaque metadata | Yes | `mellivor_kernel.memory.vector` | Medium: metadata portability must be documented |
| `VectorMatch` | Ranked record and comparable-within-query score | Yes | `mellivor_kernel.memory.vector` | Medium: score semantics need adapter proof |
| `VectorStore` | Structural persistence/search seam | Yes | `mellivor_kernel.memory.vector` | Medium: second backend must prove portability |
| `VectorStoreError` | Translated vector-backend failure | Yes | `mellivor_kernel.memory.vector` or memory exceptions | Low |

No registry, factory, facade, collection object, filter DSL, pagination type,
distance enum, ingestion service, or RAG type is justified yet. Public package
re-exports should wait until the contract is implemented, tested, and
dogfooded; provider-specific adapters remain explicit optional-module imports,
following current provider convention.

This placement extends two existing responsibilities rather than creating a
twelfth ADR-0002 responsibility: embedding adapters are model-provider
infrastructure, while vector persistence/search is memory infrastructure. The
modules must remain dependency-independent. `memory.vector` must not import
`providers.embeddings`, and the embedding module must not import memory.

## Concrete backend proof strategy

The contract must be proven through composition, not only structural fakes.
After a Proposed ADR is accepted, the smallest implementation sprint should:

1. implement the minimal contracts above;
2. add one optional OpenAI-compatible embedding adapter using an injected HTTP
   transport and explicit configuration;
3. add an `InMemoryVectorStore` using exact, deterministic search as a
   reference/test backend, explicitly not a production-scale index; and
4. exercise embedding result → vector upsert → similarity query end to end
   with synthetic data, without prompt construction or answer generation.

A second, genuinely external vector backend selected from a consuming
product's deployment evidence should follow before the vector contract is
declared broadly proven. That backend—not this challenge—should decide whether
pgvector, Qdrant, Pinecone, or another infrastructure target is appropriate.

Standard-library SQLite is not an honest first production vector backend. It
has no built-in vector type, distance operator, or approximate index. A Python
full scan over SQLite blobs would demonstrate persistence while misleading
consumers about vector-search semantics and scalability. A named SQLite vector
extension could be evaluated later as an optional backend, with its binary
distribution, loading, metric, concurrency, and portability constraints made
explicit; it must not be conflated with `SQLiteMemoryStore`.

## SemVer assessment

The architecture can be introduced additively in v1.x if implementation:

- adds new modules/types without removing or changing existing exports;
- does not add an abstract method or new constructor requirement to
  `BaseProvider`;
- does not reinterpret `ProviderCapabilities.supports_embeddings`;
- does not change `MemoryStore`, `MemoryEntry`, `MemoryQuery`, or
  `MemoryResult`;
- does not add fields to frozen public dataclasses;
- does not add a new `ExecutionTarget` or change dispatcher behavior; and
- keeps third-party backends in optional extras.

No MAJOR version is required by the proposed design. Extending
`BaseProvider`, changing text-memory search to ranked semantic search, or
making vector dependencies mandatory would require a separate compatibility
review and may be breaking; none is recommended.

## Risks

- A one-backend contract may accidentally encode that backend's metric,
  namespace, consistency, or filtering model.
- Python tuples are dependency-free and deterministic but can be expensive for
  large batches; introducing NumPy into the public contract would impose a
  mandatory dependency and is rejected initially.
- “Namespace” can be mistaken for an authorization guarantee unless every
  specification repeats the trust boundary.
- Backend-native scores differ; only within-query ordering is portable.
- Metadata types, serialization, and size limits vary across stores.
- Synchronous APIs can block; premature dual sync/async APIs would double the
  public surface before demand is demonstrated.
- In-memory exact search proves behavior but not production scalability or
  external-backend portability.
- Embedding model changes can alter dimensions and invalidate stored vectors;
  lifecycle/migration remains caller-owned.

## Open questions for the Proposed ADR

1. Does a concrete consumer require per-request model selection, or is one
   configured model per provider instance sufficient?
2. Which OpenAI-compatible embedding response variants are in the first
   adapter's supported protocol subset?
3. Which exact similarity metric should `InMemoryVectorStore` use, and should
   it be fixed at construction without a public enum?
4. Are metadata values limited to JSON-compatible values in the portable
   contract, or is serialization entirely implementation-specific?
5. Must a second external store ship in the same release before exporting
   `VectorStore`, or is an explicitly provisional first implementation
   acceptable under the dogfood principle?
6. Which consuming product and deployment will select the first external
   backend and provide real integration evidence?

## Recommendation

Product Owner should approve the partial boundary before any feature work.
If approved, create a Proposed ADR that fixes the minimal contracts and closes
the open questions. Only after that ADR is reviewed should a narrowly scoped
implementation sprint be opened. RAG and all product retrieval policy remain
Future Research/product scope.
