# 0009. Memory subsystem, and execution recording through it

Status: Accepted
Date: 2026-07-23

## Context

[ADR-0002](0002-ai-enterprise-kernel-scope-and-subsystems.md) names
**Memory abstraction** as a fixed kernel responsibility with a reserved
package (`memory/`) since Sprint 1, but no implementation — the same
situation `events` was in before Sprint 9
([ADR-0008](0008-event-bus-and-lifecycle-events.md)). This sprint
implements it, and wires `ExecutionEngine` to optionally record execution
outcomes through it.

This requires an ADR on the same grounds as ADR-0008: it defines a new
contract (`MemoryStore`) another subsystem (`execution`) now depends on,
and it changes `ExecutionEngine`'s behavior (optionally, additively).

## Decision

**A new top-level package, `src/mellivor_kernel/memory/`,** implements
text memory as kernel infrastructure -- explicitly **not** an LLM
feature, and with **no dependency on any provider, workflow, or agent
concept**, now or in any planned future: `memory` depends only on `core`
(for `MemoryError`). The intended dependency direction, once a future
subsystem needs it, is a provider *consuming* memory (reading it), never
memory depending on a provider:

- `MemoryEntry` — an immutable text record (`id`, `content`, `tags`,
  `metadata`, `created_at`). `id` is a caller-chosen, stable key, not an
  auto-generated correlation token like `ExecutionRequest.request_id` --
  `add()`-ing an existing `id` overwrites, by design.
- `MemoryQuery` — an immutable, deterministic filter set (`id`, `tag`,
  `metadata`, `text`), AND-combined. No embeddings, no vector search, no
  ranking — an unset filter matches everything, a set filter is an exact
  or substring match.
- `MemoryResult` — the immutable outcome of a search: a tuple of matching
  `MemoryEntry` values, empty (not an error) when nothing matches.
- `MemoryStore` — a `Protocol` (`add`, `get`, `search`, `delete`,
  `clear`): the contract every backend satisfies. Consumers depend on
  this Protocol, never on a concrete backend — the same seam
  `EventBus`/`Authorizer` already established.
- `InMemoryStore` — the only concrete implementation this sprint adds:
  a plain dict keyed by `id`, no persistence, no external dependency.
- `Memory` — a stable facade wrapping a `MemoryStore` (defaulting to
  `InMemoryStore` if none given), itself structurally satisfying
  `MemoryStore` -- so a `Memory` instance can be handed anywhere a
  `MemoryStore` is expected.
- `MemoryError` — raised only for invalid data (a malformed
  `MemoryEntry`); a missing lookup (`get`) or an empty search result is a
  normal, non-raising outcome (`None` / an empty `MemoryResult`).

**Scope is deliberately text-only.** No embeddings, vector database,
semantic search, RAG, persistence, SQL, Redis, Pinecone, Chroma, or FAISS
-- all left for a future milestone, once a real need for them is
established, per this sprint's explicit instruction.

**`ExecutionEngine` gains an optional `memory: MemoryStore | None = None`
constructor parameter.** With no memory configured (the default),
behavior is byte-for-byte identical to Sprint 9/10 — verified by the full
prior test suite passing unmodified. When configured, `ExecutionEngine`
records every execution's outcome as a `MemoryEntry` (keyed by
`request.request_id`) immediately after publishing the terminal event
(`ExecutionCompleted`/`ExecutionFailed`), for both successful and failed
outcomes, including an authorization denial. `content` is a plain
`str()` of the result's payload (or its error, on failure) -- a
deliberately simple, generic text representation; no payload-to-text
schema is invented per target type. A memory backend's own exception is
caught and logged, never propagated: a misbehaving `MemoryStore` must
never break execution, the same resilience guarantee `InMemoryEventBus`
already gives handlers.

**No provider, `Dispatcher`, or `ExecutionContext` change.** Memory
recording is entirely `ExecutionEngine`'s own responsibility, the same
way event publication already is — `Dispatcher` and `BaseProvider` are
untouched, and `ExecutionContext`'s four fields (fixed by ADR-0006,
"deliberately no more") are not expanded.

## Alternatives considered

- **Thread memory through `ExecutionContext` instead of `ExecutionEngine`'s
  constructor.** Rejected: `ExecutionContext` is explicitly documented as
  fixed at four fields; adding a fifth would either break every existing
  caller (no default possible without one) or blur the line ADR-0006 drew.
  `ExecutionEngine`'s own optional constructor parameter is the same
  pattern already proven safe for `authorizer` and `event_bus`.
- **Have `Dispatcher` or `BaseProvider` read from/write to memory
  directly**, so a provider could use prior memory as conversation
  context. Rejected for this sprint: the instruction is explicit that no
  provider changes are required, and doing so would require inventing a
  request-augmentation convention (which field a provider reads memory
  from) that is exactly the kind of design decision better made once
  `agents`/`workflow` establish a real multi-turn use case, not guessed
  here.
- **Auto-generate `MemoryEntry.id` like `ExecutionRequest.request_id`.**
  Rejected: the "overwrite" requirement only makes sense if `id` is a
  caller-chosen, reusable key; `ExecutionEngine`'s own recording already
  supplies `request.request_id` as that key, but a caller building
  entries directly needs to choose meaningful, reusable ids of their own.
- **Raise from `get()`/`search()` on no match**, mirroring
  `ToolRegistry.lookup()`/`ProviderRegistry.get()`. Rejected: unlike a
  registry (where "not registered" is typically a caller error), an empty
  memory is a completely ordinary outcome, especially for a fresh store —
  `get()` returning `None` and `search()` returning an empty `MemoryResult`
  matches Python's own `dict.get()` convention and needs no exception
  handling for the common case.

## Consequences

- `memory` has zero dependency on `providers`, `execution`,
  `authorization`, `events`, or `tools`; only `execution` depends on
  `memory` (for `MemoryEntry`/`MemoryStore`), a normal dependency on
  generic infrastructure, the same relationship `execution` already has
  with `events`.
- Any future subsystem (a provider wanting conversation history, `agents`,
  `workflow`) that wants to *read* memory depends on `memory.MemoryStore`/
  `memory.Memory` directly; `memory` will never depend back on any of them
  -- this ADR fixes that direction as a permanent constraint, not just a
  starting point.
- `docs/architecture.md` records `memory` as implemented, the same way
  `events` was recorded in Sprint 9 — it already had its reserved package
  slot per ADR-0002, so no new "placement" heading is needed, only a
  status update.
- Introducing an actual request-augmentation mechanism (a provider reading
  prior memory before a call) is future work requiring its own design
  decision once a concrete consumer (most likely `agents`) needs it.
