# `memory` subsystem spec

Status: Implemented (Sprint 11); second, persistent implementation added
(Sprint 27).

Public contract exported from `mellivor_kernel.memory`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md). See
[ADR-0009](../adr/0009-memory-subsystem-and-execution-recording.md) for
why this subsystem exists, its dependency direction, and what it
deliberately excludes.

## Exceptions

`memory/exceptions.py` — subclasses `core.exceptions.KernelError`.

- `MemoryError` — the only exception this subsystem raises, and only for
  invalid data: a malformed `MemoryEntry`. A missing lookup or an empty
  search result is never an exception — see `get()`/`search()` below.

## `MemoryEntry`

An immutable (`frozen=True, slots=True`) dataclass — a single text memory
record:

```python
id: str
content: str
tags: frozenset[str] = field(default_factory=frozenset)
metadata: Mapping[str, object] = field(default_factory=dict)
created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

`id` is caller-chosen and stable — not auto-generated like
`execution.ExecutionRequest.request_id`. `add()`-ing an entry whose `id`
already exists in the store overwrites the previous entry; this is the
whole point of `id` being caller-supplied rather than generated.
`__post_init__` rejects a blank `id` or `content`, raising `MemoryError`.

## `MemoryQuery`

An immutable (`frozen=True, slots=True`) dataclass — the input to
`search()`:

```python
id: str | None = None
tag: str | None = None
metadata: Mapping[str, object] = field(default_factory=dict)
text: str | None = None
```

Every filter that is set must match (AND semantics); an unset filter
imposes no constraint, so `MemoryQuery()` matches every entry. `text` is a
plain, case-sensitive substring check against `content` — no embeddings,
no ranking, no fuzzy matching. `metadata` requires every given key/value
pair to be present and equal on the entry's own `metadata`.

## `MemoryResult`

An immutable (`frozen=True, slots=True`) dataclass — the outcome of a
search:

```python
entries: tuple[MemoryEntry, ...] = field(default_factory=tuple)
```

Supports `len()` and iteration directly. Empty — not an exception — when
nothing matches.

## `MemoryStore` (Protocol)

A `@runtime_checkable` `Protocol` — the contract every backend satisfies:

```python
def add(self, entry: MemoryEntry) -> None
def get(self, entry_id: str) -> MemoryEntry | None
def search(self, query: MemoryQuery) -> MemoryResult
def delete(self, entry_id: str) -> bool
def clear(self) -> None
```

Consumers (`execution.ExecutionEngine`, `memory.Memory`) depend on this
Protocol, never on `InMemoryStore` concretely — the same seam pattern
`events.EventBus` established in Sprint 9.

- `get()` returns `None` for a missing id — never raises. Unlike a
  registry lookup, a memory miss is an entirely ordinary outcome.
- `delete()` returns `True`/`False` for whether something was actually
  removed — never raises for an unknown id.
- `search()` never raises; an unmatched query returns an empty
  `MemoryResult`.

## `InMemoryStore`

The first concrete `MemoryStore` implementation (Sprint 11): a plain
`dict[str, MemoryEntry]` keyed by `id`. Not persistence — entries do not
survive process restart. `search()` performs a single linear scan
applying every set `MemoryQuery` filter; no index, no embeddings.

## `SQLiteMemoryStore`

The second concrete `MemoryStore` implementation (Sprint 27) — durable,
backed by a single SQLite database file, using only the Python standard
library (`sqlite3`): no new dependency, mandatory or optional. See
[ADR-0021](../adr/0021-persistent-memory-sqlite-store.md) for the full
design rationale.

```python
def __init__(self, path: str | Path) -> None
```

`path` is required — there is no default location; storage ownership
stays with the caller, per [ADR-0004](../adr/0004-public-api-philosophy.md)'s
"no implicit global state." The parent directory must already exist.

Same five-method contract, same behavior as `InMemoryStore` for every
case the Protocol specifies, including overwrite semantics (`add()`ing an
existing `id` updates it in place, preserving its original position in
`search()` results — not a delete-and-reinsert). One backend-specific
constraint beyond the Protocol: `tags` and `metadata` values must be
JSON-serializable; a non-serializable `metadata` value raises
`MemoryError` from `add()`.

Every other `sqlite3`-level failure (a corrupt or non-SQLite file at
`path`, a missing parent directory, any I/O error) is translated to
`MemoryError` at the point it occurs — never a raw `sqlite3` exception
across the public boundary, per ADR-0004. Opening an existing, corrupt
file fails immediately from `__init__` (fail-fast; the store never
silently treats corruption as an empty store).

Not safe to share across threads without external synchronization (the
same limitation `InMemoryStore` has as an unlocked `dict`). Safe for
multiple processes to open the same file concurrently — SQLite's own
file-level locking (WAL journal mode) governs that access; no
kernel-level locking is added on top.

Additive beyond the `MemoryStore` Protocol: `close()` and context-manager
support (`__enter__`/`__exit__`) for deterministic release of the file
handle. Neither is required — the OS reclaims the handle at process exit.

No encryption at rest and no access control beyond OS filesystem
permissions on `path` — consistent with `security`/`observability`'s
"bring your own backend" posture; encryption at rest remains `Future
research` per ADR-0019.

## `Memory`

A stable facade over a `MemoryStore` backend, defaulting to a fresh
`InMemoryStore()` if none is given:

```python
def __init__(self, store: MemoryStore | None = None) -> None
```

Exposes the identical `add`/`get`/`search`/`delete`/`clear` methods,
delegating to `store`. Structurally satisfies `MemoryStore` itself, so a
`Memory` instance can be passed anywhere a `MemoryStore` is expected —
including `ExecutionEngine`'s `memory` parameter (see below).

**v1.0 scope note (Sprint 25 Public API Freeze Audit).** `Memory` has no
production consumer anywhere in the kernel today — every real usage
(`execution`, `ai_engine`) passes an `InMemoryStore` or another
`MemoryStore`-conforming object directly, never a `Memory` instance.
`Memory` is proven by its own unit tests, not by internal usage. This is
ratified as intentional, stable `1.0.0` scope: a facade offered for a
consuming product's convenience, not required by anything in the kernel
itself, the same "foundation ships ahead of its consumer" shape ADR-0012/
ADR-0013 already used for `security`/`observability`. No code change
results from this ratification.

## Integration: `execution`

`ExecutionEngine.__init__` gained an optional `memory: MemoryStore | None = None`
parameter in this sprint. With no memory configured, behavior is
byte-for-byte identical to before this sprint.

When configured, `execute()` records the outcome of every request as a
`MemoryEntry` immediately after publishing its terminal event
(`ExecutionCompleted`/`ExecutionFailed`) — for both successful and failed
outcomes, including an authorization denial:

```python
MemoryEntry(
    id=request.request_id,
    content=str(result.payload) if result.success and result.payload is not None else result.error,
    tags=frozenset({request.target.value}),
    metadata={"operation": request.operation, "success": result.success},
)
```

`content` is a deliberately simple `str()` of the payload (or the error,
on failure) — no per-target-type text schema is invented. A memory
backend's own exception during `add()` is caught and logged
(`WARNING`), never propagated — a misbehaving `MemoryStore` must never
break execution, the same guarantee `InMemoryEventBus` already gives a
failing event handler.

See `docs/specs/execution.md` for `ExecutionEngine`'s full contract.

## Dependency relationship

```
execution → memory
```

`memory` depends only on `core` (`KernelError`) plus, for
`SQLiteMemoryStore`, the Python standard library (`sqlite3`, `json`,
`pathlib`, `datetime`) — no third-party dependency, mandatory or
optional. **No dependency on `providers`, `execution`, `authorization`,
`events`, or `tools`**, and none is ever planned; see ADR-0009 for why
this direction is fixed permanently, not just a starting point.
`execution` depends on `memory` (`MemoryEntry`, `MemoryStore`) the same
way it already depends on `events` (`Event`, `EventBus`).
