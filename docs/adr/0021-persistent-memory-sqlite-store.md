# 0021. Persistent memory: `SQLiteMemoryStore`

Status: Accepted
Date: 2026-08-26

## Context

[ADR-0009](0009-memory-subsystem-and-execution-recording.md) shipped
`memory` with exactly one concrete `MemoryStore` implementation,
`InMemoryStore`, deliberately non-persistent, and explicitly designed so
"a future persistent or vector-backed store satisfies this same contract
as a drop-in replacement, with no change required to any consumer." Both
[ADR-0019](0019-release-readiness-and-scope-lock.md) and
[ADR-0020](0020-release-decision-v1.0.md) classify "a second, persistent
`MemoryStore` implementation" as `Deferred to v1.1`, scoped by name, with
no further design gate required before scheduling it — mirroring the
precedent already set twice for `providers` (`ClaudeProvider`, then
`OpenAIProvider`): a second concrete implementation proving an existing
contract, not a contract change.

This is Sprint 27, the first Product-Owner-approved sprint of the v1.1
line (`docs/architecture/roadmap.md`), per direct instruction: "Add a
second, durable `MemoryStore` implementation that proves the existing
memory abstraction works beyond the in-memory implementation," with the
v1.0.0 public API and behavior fixed as the compatibility baseline.

**Architecture review finding.** Before writing this ADR, the existing
`MemoryStore` Protocol (`src/mellivor_kernel/memory/store.py`),
`MemoryEntry`, `MemoryQuery`, `MemoryResult`, `MemoryError`, and their
tests (`tests/memory/`) were inspected in full, together with ADR-0009,
ADR-0019, and the frozen v1.0 public API (`docs/specs/memory.md`). No
architectural conflict was found: `MemoryStore` is already a minimal,
five-method structural `Protocol` (`add`/`get`/`search`/`delete`/`clear`)
with no assumption anywhere that a backend is in-process or ephemeral. A
persistent implementation satisfies it with **zero change** to
`MemoryStore`, `MemoryEntry`, `MemoryQuery`, `MemoryResult`,
`MemoryError`, `InMemoryStore`, or `Memory`. This ADR proceeds on that
basis; per this sprint's own instruction, had a conflict been found, this
ADR would stop and report it instead.

## Decision

**A new module, `src/mellivor_kernel/memory/sqlite_store.py`, adds
`SQLiteMemoryStore`** — a `MemoryStore` implementation backed by a single
SQLite database file, using Python's standard-library `sqlite3` module.
Exported from `mellivor_kernel.memory.__all__` alongside the existing five
names; nothing already exported changes shape or behavior.

**Why SQLite, not a new dependency.** `pyproject.toml` declares
`dependencies = []`; every optional integration to date (`anthropic`,
`openai`) is a third-party *vendor* SDK behind its own extra, because
those genuinely require an external service and a maintained client.
Durable local storage requires neither: `sqlite3` ships in the Python
standard library on every supported interpreter (3.12/3.13), so this adds
**zero new dependency, mandatory or optional** — no new
`[project.optional-dependencies]` entry, no change to CI. This is the
better fit for "the most appropriate persistence technology based on the
repository's existing dependency philosophy" than a file-per-entry JSON
store (worse durability/corruption guarantees, no atomic multi-row
transactions) or a third-party embedded KV library (an unjustified new
dependency for a contract five methods wide).

**Persistence model.** One SQLite database file per `SQLiteMemoryStore`
instance, one table (`memory_entries`), one row per `MemoryEntry`, keyed
by `id` (`TEXT PRIMARY KEY`). No sharding, no multi-file layout, no
separate index files beyond what SQLite manages internally.

**Storage ownership.** The caller supplies the file path explicitly to
the constructor (`SQLiteMemoryStore(path)`); there is no default path and
no implicit location the kernel chooses on the caller's behalf, per
[ADR-0004](0004-public-api-philosophy.md)'s "no implicit global state" —
configuration ownership, including where a store's data lives, stays with
the consumer. The store opens the given path as-is and does not create
missing parent directories; a missing parent directory is a caller
configuration error, surfaced as `MemoryError` (see "Failure semantics"
below), not silently corrected. The store never deletes its own backing
file — file lifecycle (creation of the parent directory, eventual
deletion of the `.sqlite` file) is entirely the caller's responsibility.

**Serialization strategy.** `content`, `id`, and `created_at`
(ISO 8601, via `datetime.isoformat()`/`datetime.fromisoformat()`) are
stored as `TEXT`. `tags` (a `frozenset[str]`) and `metadata`
(`Mapping[str, object]`) are stored as `TEXT` columns holding JSON
(`json.dumps`/`json.loads`). This introduces one backend-specific
constraint beyond what the Protocol itself requires: **`tags` and
`metadata` values must be JSON-serializable** for this backend. A
non-serializable `metadata` value raises `MemoryError` from `add()` —
consistent with `MemoryError`'s existing, documented scope ("raised only
for invalid data"), not a change to when `MemoryError` is raised in
general. `InMemoryStore` has no such constraint and none is added to it;
this is `SQLiteMemoryStore`-specific, documented in its own docstring and
in `docs/specs/memory.md`, the same way each provider documents its own
backend-specific exception mapping.

**Lifecycle.** The connection opens in `__init__` and stays open for the
instance's lifetime; `close()` and context-manager support
(`__enter__`/`__exit__`) are added for deterministic cleanup of the
underlying file handle — purely additive methods beyond the `MemoryStore`
Protocol's five, the same way `Memory` and `InMemoryStore` are free to
have implementation-specific surface a Protocol doesn't forbid. Not
using the store as a context manager and never calling `close()` is
supported and safe (the OS reclaims the handle at process exit); `close()`
exists for callers who want deterministic release, e.g. within a `with`
block in a test or a short-lived script.

**Concurrency behavior.** A single `SQLiteMemoryStore` instance is not
safe to share across threads without external synchronization —
`sqlite3.connect(..., check_same_thread=True)` (the default) enforces
this at the connection level, raising rather than silently corrupting
state. This is a deliberate parity choice with `InMemoryStore`, which is
equally not thread-safe (a plain `dict` with no internal locking); neither
backend claims a guarantee the other doesn't. Cross-process concurrent
access to the *same file* — the actual "durable across process
recreation" scenario this sprint targets — is handled by SQLite's own
file-level locking, made more robust than the default rollback-journal
mode by two `PRAGMA`s set once per connection: `journal_mode=WAL`
(concurrent readers do not block a writer) and `synchronous=NORMAL` (the
standard, well-documented production pairing for WAL mode). No
kernel-level locking layer is added on top — SQLite's own concurrency
control is production-grade and sufficient for this contract's scope.

**Failure semantics.** Every `sqlite3.Error` raised by the underlying
connection — at open time (table creation) or during any of
`add`/`get`/`search`/`delete`/`clear` — is caught and re-raised as
`memory.MemoryError`, chaining the original via `raise ... from exc`. No
raw `sqlite3` exception ever crosses the `MemoryStore` boundary, per
ADR-0004's "errors are translated at the boundary" — the same discipline
`providers` already applies to vendor SDK exceptions. `get()`, `search()`,
and `delete()` continue to never raise for an ordinary miss (a missing
id, an empty search, an unknown id to delete) — only a genuine
storage-level failure raises.

**Corruption behavior.** If the path given already exists but is not a
valid SQLite database, the `CREATE TABLE IF NOT EXISTS` statement run at
construction time fails with `sqlite3.DatabaseError`, translated to
`MemoryError` and raised immediately from `__init__` — the store never
opens. This is a deliberate fail-fast choice: silently treating a corrupt
file as an empty store would discard whatever was recoverable and mask
data loss; refusing to open lets the caller decide (restore from backup,
delete and recreate, investigate) rather than the kernel deciding for
them.

**Compatibility guarantees.** No change to `MemoryStore`, `MemoryEntry`,
`MemoryQuery`, `MemoryResult`, `MemoryError`, `InMemoryStore`, or
`Memory` — verified by the full pre-existing test suite (717 tests)
passing unmodified. `SQLiteMemoryStore` is a purely additive export; per
[ADR-0005](0005-versioning-strategy.md) this is a MINOR-compatible
addition, consistent with the `1.1.0` line this sprint opens.

**Cleanup/deletion semantics.** `delete(entry_id)` removes exactly one
row and returns whether one existed, matching `InMemoryStore` exactly.
`clear()` removes every row but leaves the table (and file) in place —
an empty, still-usable store — the same behavior `InMemoryStore.clear()`
has on its dict. Neither method ever deletes the backing file itself.

**Deterministic behavior.** `MemoryResult.entries` is documented as "the
matching entries, in the backing store's own order" — not a literal
cross-backend ordering guarantee. `SQLiteMemoryStore` returns rows
ordered by SQLite's implicit `rowid` (stable insertion order for a
`TEXT PRIMARY KEY` table that is not declared `WITHOUT ROWID`). `add()`
uses `INSERT ... ON CONFLICT(id) DO UPDATE`, not delete-and-reinsert, so
overwriting an existing `id` updates it in place and **preserves its
original position** — matching `InMemoryStore`'s own overwrite behavior
(reassigning an existing `dict` key does not move it). This equivalence
was a deliberate design choice, not an accident of the SQL used; a naive
`INSERT OR REPLACE` would have silently changed overwrite ordering
relative to `InMemoryStore` and was rejected for exactly that reason.
`search()`'s filter predicate (`id`/`tag`/`metadata`/`text`, AND-combined)
is the same logic as `InMemoryStore`'s, intentionally duplicated rather
than shared (see "Alternatives considered") to guarantee identical
matching semantics without a cross-module dependency on a private
helper.

**Security considerations.** The database file may contain arbitrary
caller-supplied text and structured data; `SQLiteMemoryStore` provides
**no encryption at rest and no access control beyond the OS filesystem
permissions on the given path** — consistent with `security`/
`observability`'s existing "bring your own backend" posture (ADR-0012/
ADR-0013) and with encryption-at-rest being explicitly `Future research`
per ADR-0019, not something this sprint introduces or promises. Every
SQL statement uses parameterized queries (`?` placeholders) exclusively;
no caller-supplied value (`id`, `content`, `tags`, `metadata`) is ever
interpolated into SQL text, precluding SQL injection regardless of
content.

**Test strategy.** `tests/memory/test_sqlite_store.py` mirrors
`tests/memory/test_in_memory.py`'s cases one-for-one (contract parity:
every scenario `InMemoryStore` is tested against, `SQLiteMemoryStore` is
tested against identically, using a `tmp_path`-backed file per test), plus
backend-specific cases neither existing suite needed: persistence across
store recreation (close, reopen the same path, confirm data survived),
malformed/corrupt file rejection at open time, non-JSON-serializable
metadata rejection at `add()`, isolation between two stores backed by
different files, and deterministic ordering across an overwrite. The
existing `tests/memory/test_in_memory.py` and `tests/memory/test_store.py`
are extended only to add a `SQLiteMemoryStore` case to
`test_store.py`'s protocol-conformance check
(`isinstance(SQLiteMemoryStore(...), MemoryStore)`); no existing test is
modified.

## Alternatives considered

- **A JSON-file-per-store implementation** (the whole store serialized to
  one `.json` file, rewritten on every mutation). Rejected: no atomic
  multi-statement transactions, weaker corruption behavior (a crash
  mid-write can leave a partially-written file with no recovery
  mechanism beyond the caller's own backup), and no built-in concurrent
  multi-process access story — everything SQLite already provides as a
  standard-library capability, at no added complexity.
- **A third-party embedded key-value library** (e.g. `diskcache`,
  `shelve` built on `dbm`). `shelve`/`dbm` were considered and rejected:
  `dbm`'s backend is platform-dependent (different modules on different
  systems, inconsistent file-locking guarantees), a worse fit for
  "deterministic" than `sqlite3`, which behaves identically across
  supported platforms. A third-party library was rejected outright: it
  would be a new dependency for a five-method contract `sqlite3` already
  satisfies from the standard library.
- **A shared, parametrized contract-test suite run against both
  `InMemoryStore` and `SQLiteMemoryStore`**, rather than a duplicated
  test file. Considered, and rejected for this sprint: it would require
  restructuring `tests/memory/test_in_memory.py`, an existing v1.0 test
  file, for a two-implementation contract where the duplication cost is
  small (one file, mirroring an existing one closely). Revisit if/when a
  third `MemoryStore` implementation ships and the duplication cost
  triples.
- **Sharing `InMemoryStore`'s private `_matches` filter function** across
  modules instead of duplicating it in `sqlite_store.py`. Rejected: it is
  a module-private helper (leading underscore, no `__all__` export);
  importing it from another module would create an undocumented,
  unintended coupling between two otherwise-independent backend modules.
  A six-line duplication is the smaller, more local cost.
- **`INSERT OR REPLACE` for `add()`'s upsert.** Rejected after
  discovering it deletes and reinserts the conflicting row, which changes
  `rowid` and therefore search-result ordering on every overwrite —
  silently diverging from `InMemoryStore`'s order-preserving overwrite
  behavior. `INSERT ... ON CONFLICT(id) DO UPDATE` was chosen specifically
  because it updates in place.
- **Adding a default file path** (e.g. under a kernel-managed temp or
  config directory) so callers could construct `SQLiteMemoryStore()` with
  no argument, mirroring `InMemoryStore()`'s no-argument constructor.
  Rejected: ADR-0004 fixes "no implicit global state" as a permanent
  public-API principle; a kernel-chosen file location is exactly the kind
  of implicit, consumer-invisible state ownership that principle
  precludes. `InMemoryStore()` needs no argument because it owns nothing
  outside the process; a durable store inherently owns a location, and
  that ownership stays with the caller.

## Consequences

- `mellivor_kernel.memory.__all__` gains one name, `SQLiteMemoryStore` —
  additive, MINOR-compatible per ADR-0005. Six existing names are
  unchanged.
- `memory` continues to depend only on `core` (`MemoryError`) plus, now,
  the standard-library `sqlite3`/`json`/`pathlib`/`datetime` modules —
  no new third-party dependency, no new `pyproject.toml`
  optional-dependency group, no CI change.
- A consuming product (Mellivor One, Mellivor AI Security) that wants
  durable memory now has a supported, zero-extra-dependency option; one
  that wants ephemeral, fastest-possible memory keeps `InMemoryStore`
  exactly as before. Nothing in the kernel's own code (`execution`,
  `ai_engine`) is changed to prefer one over the other — the choice
  remains entirely the consumer's, per `MemoryStore`'s existing
  dependency-injection seam.
- `SQLiteMemoryStore` introduces exactly one new, backend-specific
  constraint not shared by `InMemoryStore`: `tags`/`metadata` values must
  be JSON-serializable. This is documented in the class docstring and
  `docs/specs/memory.md`, not silently discovered by a caller at runtime.
- No encryption at rest is added. A consumer with an encryption-at-rest
  requirement must apply it at the filesystem layer (e.g. an encrypted
  volume) or wait for `Future research` to schedule it — this ADR neither
  promises nor precludes that.
- Sprint 28 (`SecretProvider` backend) faces a structurally similar
  "concrete implementation, zero new dependency" decision; this ADR's
  reasoning (standard-library-first, explicit storage ownership,
  boundary-translated failures) is the precedent it should be checked
  against, though it will need its own ADR per this sprint's own
  instruction, not an extension of this one.
