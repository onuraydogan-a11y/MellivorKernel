# Experimental embedding and vector contracts

Status: internal architecture proof (Sprint 36)

ADR-0027 defines two independent experimental seams. They are implemented
under private modules and are not part of Mellivor Kernel's stable v1.x public
API:

- `providers._embeddings` contains the synchronous, batch-first embedding
  contract and a direct-HTTP OpenAI-compatible proof adapter.
- `memory._vector` contains vector values, the vector-store protocol, and a
  dependency-free `InMemoryVectorStore` proof backend.

The embedding adapter uses a caller-configured endpoint and model. It does not
use the OpenAI SDK, start or manage a runtime, download a model, probe the
network during import or construction, or fall back to a cloud provider.
HTTPX is owned directly by the optional `embeddings` extra. Protocol validation
is deterministic and mocked; no runtime-specific interoperability claim is
made.

`InMemoryVectorStore` provides process-local, nonpersistent, non-thread-safe,
exact cosine search. Dimensions are fixed at construction. Every operation
requires a namespace, which is only a routing and isolation key—not
authentication or authorization. Query results are ordered by descending
similarity score and then ascending record ID for exact ties. Missing fetch IDs
are omitted; deletion is idempotent.

Both boundaries validate and defensively snapshot their values. Generated
errors do not include input text, vectors, metadata, credentials,
authorization headers, or raw response bodies. A store deletion confirms only
logical removal from that store; it makes no physical-erasure guarantee.

This proof deliberately excludes stable exports, RAG, chunking, ingestion,
ranking or reranking policy, prompt construction, citations, product
authorization, external vector databases, filtering, pagination, hybrid
search, collection administration, and runtime lifecycle management. A second
backend requires Product Owner approval and concrete consumer deployment
evidence before the abstraction may be described as broadly proven.
