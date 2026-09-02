# Sprint 37: External vector backend consumer evidence and selection

Status: Complete — no backend selected; current consumers do not yet need
external vector storage

Date: 2026-09-02

## Purpose and decision boundary

This review evaluates whether a real Mellivor consumer and its deployment
provide enough evidence to select the materially different external
`VectorStore` backend required by ADR-0027's second-backend gate. It does not
select infrastructure from general market popularity and does not treat a
future product idea as a deployment requirement.

**Decision: E — DEFER; CURRENT CONSUMERS DO NOT YET NEED VECTOR STORAGE.**

No external backend is selected. PostgreSQL/pgvector is the best-aligned
candidate to reassess if Mellivor One approves a concrete retrieval workload,
but existing PostgreSQL does not by itself prove a need for pgvector. Qdrant
and other dedicated services have no current deployment or operational-owner
evidence. The ADR-0027 contracts remain internal and experimental, and the
public-export gate remains closed.

## Evidence method

The audit used the current Mellivor Kernel repository and read-only evidence
from the sibling `MellivorAISecurity` and `MellivorOne` repositories available
in the development workspace. Product evidence was limited to committed
architecture, ADR, roadmap, dependency, application, and deployment material;
working-tree changes in those repositories were not used as authority.

The Kernel repository itself names Mellivor One and future enterprise products
as consumers, but contains no product deployment manifests, PostgreSQL or
vector-service configuration, retrieval workload, scale estimate, or
operational ownership assignment. ADR-0027 therefore correctly requires
evidence from consuming deployments before a second backend is approved.

## Consumer evidence audit

### Mellivor AI Security

Evidence reviewed includes `README.md`, `pyproject.toml`, ADR-0008, ADR-0038,
ADR-0042, the enterprise architecture and operations specifications, and the
persistence/deployment packages in the `MellivorAISecurity` repository.

| Question | Evidence |
|---|---|
| Retrieval/vector use case | None is defined or scheduled. Security detection, policy, audit, provider intelligence, quarantine, and console capabilities use deterministic domain repositories rather than semantic retrieval. |
| Need for embeddings/vector search | Not established. Earlier Kernel architecture material mentions AI-security context lookup as a possible class of use, not a Mellivor AI Security requirement. |
| Expected scale | No vector corpus, query-rate, latency, dimension, or growth target exists. |
| Persistence | Current durable product repositories use standard-library SQLite. |
| Isolation | SaaS uses tenant-scoped records in a shared deployment; Private Cloud is customer-scoped; On-Prem prohibits unapproved external network dependencies. Product authorization must precede any Kernel namespace mapping. |
| Deployment topology | No staging deployment has occurred. The executable supports SaaS, Private Cloud, and On-Prem shapes; the current durable strategy defaults to a single-writer/active-passive SQLite topology. |
| Operational ownership | The product owns deployment, credentials, encryption, backups, retention, and data residency. No vector service owner is named. |
| Existing external vector backend | None. No pgvector, Qdrant, or other vector-service dependency/configuration exists. |

ADR-0038 permits a future client-server database only after a concrete
multi-host concurrent-write requirement and a dedicated dependency/security
decision. ADR-0042 makes a mandatory hosted vector service especially
incompatible with the On-Prem constraint. Mellivor AI Security supplies no
basis for selecting an external vector backend now.

### Mellivor One

Evidence reviewed includes ADR-005, ADR-010, ADR-014, the deployment guide,
cloud setup, runtime requirements/configuration, AI Studio v1 scope, the AI
module description, and current product roadmaps in the `MellivorOne`
repository.

| Question | Evidence |
|---|---|
| Retrieval/vector use case | `docs/modules/ai.md` describes RAG as something that *may* be used and a vector database as a future structure. It does not approve or schedule a corpus, ingestion flow, retrieval policy, or product feature. Current AI Studio v1 explicitly closes scope around runtime, providers, tools, contract intelligence, agents, prompts, memory, and events. |
| Need for embeddings/vector search | Plausible for future enterprise knowledge and document intelligence, but not currently demonstrated. The roadmap contains no committed vector-storage delivery. |
| Expected scale | No vector count, tenant count for this workload, query throughput, latency SLO, dimensions, index size, or retention period is specified. |
| Persistence | PostgreSQL is the accepted platform database. Current implementation also contains transitional SQLite paths. Control Plane PostgreSQL and dedicated tenant PostgreSQL databases are real architecture and code concerns. |
| Isolation | ADR-010 requires database-per-tenant for business data, with a separate shared Control Plane containing platform metadata only. This is stronger than a shared-table namespace convention. |
| Deployment topology | A Flask/gunicorn modular monolith can use managed PostgreSQL. The deployment guide names Neon, Supabase, Railway, and DigitalOcean as possible providers, but does not establish one authoritative provider for all deployments. |
| Operational ownership | Mellivor One owns tenant resolution, database provisioning, credentials, migrations, backup/restore, disaster recovery, and authorization. Kernel may only receive an already-authorized namespace/store configuration. |
| Existing external vector backend | None. The AI module lists PostgreSQL Vector, Pinecone, Weaviate, and Qdrant as future options, explicitly without selecting one. No vector client, extension migration, configuration, or runtime path exists. |

Mellivor One provides genuine PostgreSQL deployment fit, but no approved
retrieval consumer. Database presence is necessary evidence for pgvector
feasibility, not sufficient evidence for backend selection.

### Other potential consumers

The Kernel repository refers generically to future Mellivor products. The
workspace also contains a minimal `CRM` directory, but it provides no Kernel
consumer architecture, deployment topology, or vector requirement. No other
consumer offers evidence suitable for this decision.

## Evidence-backed candidate evaluation

Only PostgreSQL/pgvector merits a serious fit analysis because Mellivor One
already uses PostgreSQL. Qdrant receives a rejection check because Mellivor
One's future-options document names it; this mention is not deployment
evidence. Pinecone and Weaviate are likewise option-list entries with no
current environment or requirement and are not evaluated further.

### PostgreSQL with pgvector

| Concern | Assessment |
|---|---|
| Deployment fit | Strongest potential fit for Mellivor One: PostgreSQL, a Python driver, managed deployment guidance, database migrations, and tenant-specific connection resolution already exist. No fit is established for Mellivor AI Security's current SQLite/On-Prem-first constraints. |
| PostgreSQL version | Not pinned or evidenced. No supported server-version floor can be asserted. |
| Extension availability | Not evidenced. No `CREATE EXTENSION vector`, extension inventory, managed-provider entitlement, or operator approval exists. |
| Operational realism | Potentially realistic on a provider/installation supporting pgvector, but enabling and upgrading the extension would require explicit database-owner approval and per-tenant migration/backup validation. It cannot be assumed across Neon, Supabase, Railway, DigitalOcean, Private Cloud, and On-Prem. |
| Dependency impact | A future adapter would require a directly declared optional PostgreSQL driver/vector adaptation dependency. It must not rely accidentally on Mellivor One's `psycopg2-binary`. No dependency is approved by this review. |
| Operational burden | Lower than a new service where pgvector is supported, but extension lifecycle, index creation, schema migrations, connection pooling, vacuum/analyze, backup/restore, and tenant-by-tenant rollout remain product/operator responsibilities. |
| Persistence/concurrency | PostgreSQL can provide durable concurrent operations; exact guarantees depend on transaction boundaries and deployment configuration. |
| Namespace/isolation mapping | For Mellivor One, the strongest mapping is an already-resolved tenant database plus an adapter-owned logical namespace column or table partition inside that database. A shared Control Plane vector table would violate ADR-010 for business data. Namespace must not select or authorize tenant credentials. Schema-per-namespace or dynamic table names would add injection/migration complexity and are not required by the contract. |
| Dimensions/cosine | pgvector can represent fixed dimensions and cosine distance. The adapter would validate dimensions and translate cosine distance to the ADR score (`1 - distance`), clamp only floating-point round-off, and reject invalid backend results. Exact index/operator/version choices require implementation evidence. |
| Determinism | SQL must explicitly order by cosine distance/derived score and caller ID. Approximate indexes can alter candidate recall, but deterministic presentation among returned candidates remains adapter-enforceable. Whether approximate retrieval is acceptable is a consumer decision not yet supplied. |
| Metadata | Scalar JSON metadata maps naturally to `jsonb`; the adapter must validate returned values and avoid inventing filtering semantics. |
| Fetch/delete | Ordered fetch requires explicit reconstruction in requested-ID order. Namespace-scoped upsert/delete and idempotent missing-ID deletion map naturally to SQL. |
| Errors/testability | Driver/database exceptions can be translated to `VectorStoreError`. Unit tests can inject a driver seam, but second-backend proof ultimately requires disposable real PostgreSQL with the extension, including concurrency and migration tests. |
| Contract impact | No known contract change is required. All identified differences are adapter-only translations, subject to real-backend proof. |

### Qdrant or another dedicated vector service

| Concern | Assessment |
|---|---|
| Deployment evidence | None. Qdrant appears only in Mellivor One's non-selected future technology list. No product currently deploys or plans an approved Qdrant service. |
| Operational ownership | Unassigned. Provisioning, upgrades, availability, credentials, TLS, backups/snapshots, retention, monitoring, capacity, and incident response would all be new responsibilities. |
| Deployment fit | A new network service would increase failure modes and conflicts with Mellivor AI Security's On-Prem/no-unapproved-external-dependency discipline unless self-hosted and explicitly owned. |
| Contract fit | Collections or payload partitioning could map namespaces; dimensions, cosine, caller IDs, payload metadata, upsert, fetch, and delete are conceptually representable. Ordered fetch and deterministic score/ID ordering would require adapter reconstruction. Backend consistency and deletion guarantees require real evidence. |
| Dependency impact | A client/HTTP dependency would need an isolated optional extra and explicit version ownership. No such dependency is justified. |
| Selection result | Rejected for this sprint due to absent consumer, deployment, and operator evidence—not because the technology is incapable. |

No other backend has enough evidence to qualify as a serious candidate.

## Contract stress test

The conceptual pgvector and Qdrant mappings do not presently expose a required
change to ADR-0027:

| Contract requirement | pgvector concept | Qdrant concept | Classification |
|---|---|---|---|
| Fixed dimensions | Typemod/schema plus adapter validation | Collection vector configuration plus adapter validation | Adapter-only translation |
| Namespace-scoped operations | Authorized tenant database plus logical namespace field | Collection/payload partition chosen by configured adapter policy | Adapter-only translation; product performs authorization first |
| Upsert/caller IDs | Primary/unique key with conflict replacement | Point ID/upsert mapping | Adapter-only translation |
| Cosine score `[-1, 1]` | Translate cosine distance and validate | Translate/validate documented cosine score | Adapter-only translation |
| Deterministic ties | Explicit descending score, ascending ID order | Adapter-side final sort by score then ID | Adapter-only translation |
| Ordered fetch/missing omission | Query then reconstruct requested order | Retrieve then reconstruct requested order | Adapter-only translation |
| Idempotent delete | Namespace-qualified `DELETE` | Namespace-qualified point deletion | Adapter-only translation |
| Scalar metadata | Validated `jsonb` | Validated payload | Adapter-only translation |

This is a paper stress test, not backend proof. Version-specific score behavior,
ID representation, transaction/consistency behavior, batch limits, approximate
index behavior, and failure translation must be verified against the selected
real backend. No experimental contract refinement or stable v1.x breaking
change is justified now.

## Security and isolation assessment

- Namespace remains an operation-level routing/isolation key, never a subject,
  tenant credential, authentication decision, or RBAC mechanism.
- Mellivor One must authorize the caller and resolve the tenant database before
  constructing/calling an adapter. Kernel must not use untrusted metadata to
  choose a database, schema, collection, credential, or endpoint.
- Database-per-tenant is the evidence-backed isolation boundary for Mellivor
  One business vectors. A namespace column can subdivide data inside the
  already-authorized tenant database; it cannot replace that database boundary.
- Credentials and endpoints must be injected from the consuming deployment,
  excluded from representations, and redacted from translated errors. Kernel
  must not log SQL parameters, vectors, metadata, connection strings, response
  bodies, or vendor diagnostics.
- TLS/network trust, encryption at rest, backup/snapshot retention, legal
  erasure, extension/service upgrades, monitoring, and incident response remain
  deployment-owner responsibilities.
- Logical delete can guarantee only that the adapter no longer fetches or
  searches a record. Physical erasure from WAL, replicas, backups, snapshots,
  logs, or vendor retention is outside `VectorStore` and must be documented by
  the consumer deployment.
- A shared external service would require explicit tenant partitioning and
  adversarial cross-tenant tests. No shared-service design is approved here.

## Public export gate review

The second-backend gate remains closed. Sprint 36 proved only the in-memory
backend. Sprint 37 found a plausible deployment-aligned candidate but did not
find a current approved consumer workload and therefore did not select or
implement a second backend.

Even after a backend is selected, implementation alone is insufficient for
stable exports. The gate requires:

1. an approved consumer use case with scale, persistence, isolation, topology,
   ownership, dimensions, and deletion/retention requirements;
2. a separate proposed implementation ADR if the Product Owner selects the
   backend;
3. real integration evidence against the materially different backend,
   including failures and namespace isolation;
4. successful dogfooding by the named consumer without contract changes; and
5. a later explicit compatibility/export decision covering public module names
   and package exports.

Until all gates pass, `mellivor_kernel.providers._embeddings` and
`mellivor_kernel.memory._vector` remain private experimental modules with no
stable v1.x compatibility promise.

## Re-entry evidence required

The next selection review should start only when a Product Owner supplies a
concrete consumer record containing:

- named product capability and owning team;
- corpus/source ownership and why vector search is necessary;
- expected vector count, dimensions, growth, query/write rate, and latency;
- persistence, consistency, concurrency, retention, backup, and deletion needs;
- tenant/isolation mapping and authorized connection-resolution flow;
- deployment environments and operational owner;
- existing PostgreSQL server versions and pgvector availability/approval, or
  an approved dedicated-service deployment; and
- acceptance criteria that can be exercised against a real backend.

For Mellivor One, pgvector should be checked first because it may reuse the
approved database-per-tenant topology. It must still compete on demonstrated
requirements, not receive automatic selection from database proximity.

## Outcome

- Selected backend: **none**.
- ADR required now: **no**; no architectural implementation choice was made.
- Contract changes: **none**.
- Stable v1.x impact: **none**.
- Dependencies: **none**.
- Public exports: **none**.
- Recommended next action: obtain an approved consumer/deployment evidence
  record before reopening backend selection.
