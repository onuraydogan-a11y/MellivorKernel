# Architecture Review — Post-Sprint 2

Status: Point-in-time report
Date: 2026-07-21
Scope: Repository state as of commit `83974f8` (`main`) — Sprint 1 (package
foundation) and Sprint 2 (Kernel Core: config, core runtime).

This report is descriptive, not decisional. It does not propose or record
any architectural change; it exists to give a clear, verified picture of
the codebase before Sprint 3 is scoped. No files were modified to produce
it.

---

## 1. Current project tree

Tracked files only (`git ls-files`), as of commit `83974f8`:

```
.github/workflows/ci.yml
.gitignore
.pre-commit-config.yaml
LICENSE
README.md
pyproject.toml

docs/
  architecture.md
  adr/
    0001-record-architecture-decisions.md
    0002-ai-enterprise-kernel-scope-and-subsystems.md
    0003-repository-boundaries.md
    0004-public-api-philosophy.md
    0005-versioning-strategy.md
    README.md
    template.md
  specs/
    README.md
    core.md
    config.md
  diagrams/
    README.md

examples/
  README.md

scripts/
  README.md

src/mellivor_kernel/
  __init__.py                 # exposes __version__ only
  version.py                  # __version__ = "0.1.0"
  py.typed                    # PEP 561 marker
  core/
    __init__.py                # public exports
    exceptions.py               # KernelError hierarchy
    contracts.py                 # KernelSettings protocol
    container.py                  # ServiceContainer (DI)
    logging.py                     # structured logging
    runtime.py                      # Kernel, KernelState, HealthStatus
  config/
    __init__.py                # public exports
    environment.py               # Environment (StrEnum)
    settings.py                   # KernelConfig, load_config
  agents/__init__.py           # empty
  workflow/__init__.py         # empty
  memory/__init__.py           # empty
  tools/__init__.py            # empty
  events/__init__.py           # empty
  plugins/__init__.py          # empty
  providers/__init__.py        # empty

tests/
  README.md
  test_version.py
  test_bootstrap.py           # end-to-end config+core integration
  config/
    test_environment.py
    test_settings.py
  core/
    test_exceptions.py
    test_container.py
    test_logging.py
    test_runtime.py
```

48 files tracked, 1 commit, branch `main`, clean working tree.

**Untracked, out of scope for this review:** an empty `design/` directory
exists at the repository root (not created by any sprint task, not
git-tracked, no content). Flagged here for visibility only — no action
taken.

---

## 2. Public APIs

Per [ADR-0004](../adr/0004-public-api-philosophy.md), the public surface is
whatever each subsystem's `__init__.py` explicitly exports via `__all__`.
Everything else is internal.

### `mellivor_kernel` (top level)

```python
__all__ = ["__version__"]
```

Deliberately minimal — unchanged since Sprint 1. Subsystem functionality is
reached via `mellivor_kernel.core` / `mellivor_kernel.config`, not the
top-level package.

### `mellivor_kernel.core`

```python
__all__ = [
    "ConfigurationError",
    "HealthStatus",
    "Kernel",
    "KernelError",
    "KernelSettings",
    "KernelState",
    "ServiceContainer",
    "ServiceRegistrationError",
    "StartupError",
    "StructuredFormatter",
    "add_file_handler",
    "configure_logging",
    "get_logger",
]
```

### `mellivor_kernel.config`

```python
__all__ = ["ConfigurationError", "Environment", "KernelConfig", "load_config"]
```

`ConfigurationError` is re-exported here from `core` for ergonomics — it is
not redefined; `core.exceptions` remains the single source of truth for the
whole exception hierarchy.

Full per-symbol contracts: [`docs/specs/core.md`](../specs/core.md),
[`docs/specs/config.md`](../specs/config.md).

---

## 3. Core runtime architecture

`src/mellivor_kernel/core/` (637 combined lines across `core` + `config`;
`core` alone: 468 lines across 6 files).

**`exceptions.py`** (24 lines) — single hierarchy: `KernelError` (base) →
`ConfigurationError`, `ServiceRegistrationError`, `StartupError`. All other
subsystems that raise kernel errors are expected to raise (a subclass of)
these; no subsystem currently defines its own exception type.

**`contracts.py`** (24 lines) — `KernelSettings`, a `@runtime_checkable`
structural `Protocol` exposing one read-only property, `log_level: str`.
This is the seam `core` uses to depend on the *shape* of configuration
without importing `config` (see §5).

**`container.py`** (109 lines) — `ServiceContainer`, a lightweight DI
container keyed by `type`:
- `register(service_type, factory, *, singleton=True)` — factory-based
  registration; singleton factories are cached lazily on first `resolve()`,
  non-singleton factories run on every `resolve()`.
- `register_instance(service_type, instance)` — registers a
  pre-constructed singleton directly.
- `resolve(service_type)` — raises `ServiceRegistrationError` if
  unregistered.
- `is_registered(service_type)` — non-raising check.
Internal state is three plain dicts (`_factories`, `_singletons`,
`_instances`); no locking, no scoping/child-container concept.

**`logging.py`** (137 lines) — `configure_logging(settings: KernelSettings)`
sets the level and a single JSON-line console handler on the
`"mellivor_kernel"` root logger; idempotent by construction (re-running it
replaces only the handler it tagged itself as owning, via a private
attribute marker, leaving other handlers — e.g. ones added by
`add_file_handler`, or by a test runner's own log capture — untouched).
`get_logger(name)` returns a child logger under that namespace.
`add_file_handler(logger, path, *, level=None)` is the "minimal" file
sink named in the Sprint 2 requirements. `StructuredFormatter` renders
records as single-line JSON (`timestamp`, `level`, `logger`, `message`,
`exc_info` if present).

**`runtime.py`** (139 lines) — `Kernel`, `KernelState`, `HealthStatus`:
- `KernelState` (`StrEnum`): `NOT_STARTED → STARTING → RUNNING → STOPPING → STOPPED`,
  plus `FAILED`.
- `Kernel(settings, container=None)` — owns a `ServiceContainer` (creates
  a default one if not supplied).
- `.start()` — valid from `NOT_STARTED`, `STOPPED`, or `FAILED` (i.e.
  retryable after failure); calls `configure_logging(self._settings)`;
  any exception during startup is caught, sets state to `FAILED`, and is
  re-raised wrapped as `StartupError`.
- `.shutdown()` — idempotent no-op unless currently `RUNNING`.
- `.health()` — returns a `HealthStatus(healthy, state, detail)` snapshot;
  `detail` is populated for `FAILED` (last failure message) and any other
  non-`RUNNING` state.

No concurrency control anywhere in `core`: `Kernel` and `ServiceContainer`
both assume single-threaded, synchronous use. This is not documented as an
explicit constraint anywhere (see §8).

---

## 4. Configuration architecture

`src/mellivor_kernel/config/` (170 lines across 3 files).

**`environment.py`** — `Environment(StrEnum)`: `DEVELOPMENT`, `TEST`,
`PRODUCTION`. Pure classification, no behavior keyed off it anywhere yet
(e.g. no environment-conditional defaults).

**`settings.py`** — `KernelConfig` is an immutable
(`@dataclass(frozen=True, slots=True)`) value object:
```python
environment: Environment = Environment.DEVELOPMENT
log_level: str = "INFO"
debug: bool = False
```
`__post_init__` validates `log_level` against
`logging.getLevelNamesMapping()` and raises `ConfigurationError` if invalid
— the only field with validation; `debug` and `environment` are
type-constrained by their annotations alone.

`load_config(env: Mapping[str, str] | None = None) -> KernelConfig` reads
three variables — `MELLIVOR_ENVIRONMENT`, `MELLIVOR_LOG_LEVEL`,
`MELLIVOR_DEBUG` — from `env` (defaulting to `os.environ`), normalizes case,
and falls back to `KernelConfig`'s own defaults for anything absent. Boolean
parsing accepts `1/true/yes/on` and `0/false/no/off` case-insensitively;
anything else raises `ConfigurationError`.

`KernelConfig` satisfies `core.contracts.KernelSettings` structurally
(matching `log_level` as a read-only string) — this is verified at
type-check time (`mypy --strict`) and exercised at runtime by
`tests/test_bootstrap.py`, but there is no explicit runtime `isinstance`
assertion anywhere that would fail loudly if that shape ever drifted.

---

## 5. Dependency relationships

```
config  ──depends on──>  core   (imports ConfigurationError from core.exceptions)
core    ──depends on──>  (nothing in mellivor_kernel; only stdlib)
```

`core` has zero imports from any sibling subsystem. Where `core.runtime`
needs configuration (to call `configure_logging`), it depends on
`core.contracts.KernelSettings` — a Protocol it owns — rather than
`config.KernelConfig`. `config.KernelConfig` satisfies that Protocol
structurally without either module importing the other. This keeps `core`
usable (and testable) with zero dependency on `config`, consistent with
`docs/architecture.md`'s statement that `core` is "the only subsystem every
other subsystem may depend on" (a claim that only holds if `core` itself
depends on nothing above it).

Composition of the two — `load_config()` feeding a `KernelConfig` into
`Kernel(...)` — happens only in test code
(`tests/test_bootstrap.py`) and is not yet wrapped in any reusable
top-level "bootstrap the whole kernel" entry point. There is currently no
module in the repository that imports both `core` and `config` other than
that one test file.

**Unimplemented subsystems** (`agents`, `workflow`, `memory`, `tools`,
`events`, `plugins`, `providers`) contain no code and therefore have no
dependency edges yet — the dependency graph above is the entire graph that
currently exists.

**External dependencies:** none at runtime (`pyproject.toml`
`dependencies = []`). Dev-only: `ruff`, `mypy`, `pytest`, `pre-commit`.

---

## 6. Extension points already available

- **`ServiceContainer.register` / `register_instance`** — the only DI seam
  in the codebase. Any future subsystem can register implementations
  against an interface type and have `core`-owned or product code resolve
  them without a compile-time dependency on the concrete class.
- **`core.contracts.KernelSettings`** — a structural contract, not a base
  class. Any object exposing a compatible `log_level` can be handed to
  `configure_logging`/`Kernel` without inheriting from anything. This is
  the pattern ADR-0004 prescribes ("contracts before implementations") and
  the only precedent for it in the code so far.
- **`load_config(env=...)`** — accepts an arbitrary `Mapping[str, str]`
  instead of always reading `os.environ`, which is what makes it testable;
  the same seam would let a future subsystem source configuration from
  somewhere other than environment variables without changing
  `KernelConfig` itself.
- **`add_file_handler` / `get_logger`** — logging is not hard-wired to the
  console; any subsystem can attach additional handlers to its own
  namespaced logger.
- **Empty subsystem packages** (`agents/`, `workflow/`, `memory/`,
  `tools/`, `events/`, `plugins/`, `providers/`) — reserved, importable
  namespaces with no code, ready to be filled in without any restructuring.

No plugin-loading mechanism exists yet despite `plugins/` being reserved
for it — "plugin loading" as a kernel capability (ADR-0002) is still
unimplemented; the *package* exists, the *capability* does not.

---

## 7. Test coverage summary

Verified by re-running the suite in an isolated environment for this
report (not by recalling prior output):

- **58 tests**, all passing (`ruff check`, `ruff format --check`, and
  `mypy --strict` also clean over all 26 source files).
- **100% statement coverage** (213/213 statements) across all of
  `src/mellivor_kernel`, including the empty `__init__.py` stubs.

| File | Tests |
|---|---|
| `tests/test_version.py` | 2 |
| `tests/test_bootstrap.py` | 1 |
| `tests/config/test_environment.py` | 4 |
| `tests/config/test_settings.py` | 20 |
| `tests/core/test_exceptions.py` | 6 |
| `tests/core/test_container.py` | 8 |
| `tests/core/test_logging.py` | 7 |
| `tests/core/test_runtime.py` | 10 |

Coverage is exhaustive for statements but not for all *interleavings*: for
example, there is no test for `ServiceContainer` under concurrent access,
and no test that exercises `Kernel.start()` racing `Kernel.shutdown()` —
consistent with both being documented (implicitly, not explicitly) as
single-threaded.

Coverage measurement itself is ad hoc: `coverage` is not a declared dev
dependency and is not run in CI (`.github/workflows/ci.yml` runs
`ruff check`, `ruff format --check`, `mypy`, `pytest` — no coverage gate or
report). The 100% figure above is accurate as of this report but nothing
would catch a regression below it.

---

## 8. Known technical debt

1. **Coverage is not enforced.** No `coverage` dependency, no CI coverage
   gate, no minimum threshold configured anywhere.
2. **Observability is one-third built.** Per ADR-0002/`docs/architecture.md`,
   "Observability" covers logging, tracing, metrics, and audit trail; only
   structured logging exists. Tracing, metrics, and audit trail are
   unaddressed and unpositioned (not even a stub package).
3. **Security primitives do not exist at all** — no code, no package, no
   spec. Named as a kernel responsibility in ADR-0002 with no owner yet.
4. **No documented concurrency model.** Neither `Kernel` nor
   `ServiceContainer` claims thread-safety, and neither is tested for it.
   If a future subsystem assumes either is safe under concurrent access,
   that assumption would be silently wrong.
5. **No kernel-wide bootstrap entry point.** Composing `config.load_config()`
   with `core.Kernel` currently only happens in a test. There's no reusable,
   documented "start the kernel from environment variables" function a
   consuming application (or a future subsystem) is meant to call.
6. **`ServiceContainer` has no un-registration, scoping, or child-container
   support.** Fine for Sprint 2's needs; will likely be a real gap once
   multiple subsystems register overlapping service types or tests need
   isolated containers per case (current tests just construct a fresh
   container per test, which works only because nothing is process-global).
7. **`Environment` is inert.** The enum exists and is validated, but
   nothing in the codebase branches on it — no environment-conditional
   defaults, no documented intended use beyond classification.
8. **Pinned pre-commit hook versions will drift.** `.pre-commit-config.yaml`
   pins `pre-commit-hooks` v4.6.0, `ruff-pre-commit` v0.6.9, and `mypy`
   v1.11.2 — all older than what Sprint 2's verification run actually used
   (ruff 0.15.22, mypy 2.3.0 were installed via the unpinned `dev` extra).
   Pre-commit and CI are currently checking against different tool
   versions.
9. **Untracked empty `design/` directory** at the repository root, origin
   unknown, not part of any sprint deliverable (noted in §1).
10. **Only 2 of 9 subsystem packages have specs** (`core.md`, `config.md`
    in `docs/specs/`). ADR-0004 expects a spec before implementation for
    each subsystem; the other seven are empty packages with no spec yet,
    which is consistent (nothing's been implemented for them) but worth
    tracking as those sprints approach.

None of the above are defects in what was built — Sprint 2's own scope is
fully tested and clean. They are gaps *relative to the full kernel* that
Sprint 3+ will need to account for.

---

## 9. Recommended next implementation order

This is a recommendation for discussion, not a decision — architecture
remains frozen per your instruction, and subsystem sequencing for Sprint 3+
is yours to set.

Reasoning from the dependency shape already visible in ADR-0002's
responsibility list: `agents` and `workflow` are consumers — they need
something to call, remember with, and announce state changes through — so
building them first would mean building their dependencies as stubs inside
them, only to extract those stubs later. The lower-dependency, higher-reuse
subsystems are better built first:

1. **`events`** (event bus) — no dependencies beyond `core`; every other
   remaining subsystem plausibly wants to publish or subscribe to
   lifecycle/state events (this is also the natural home for the rest of
   "Observability" — an event bus is a common backbone for later
   tracing/audit work, though that's a future decision, not this one).
2. **`tools`** (tool execution) — no dependencies beyond `core` (and
   optionally `events`, to emit invocation events). Needed by both `agents`
   and `workflow` later.
3. **`memory`** (memory abstraction) — no dependencies beyond `core`.
   Needed by `agents` for state/context persistence.
4. **`providers`** (multi-LLM abstraction) — depends on `core`
   (`ConfigurationError` for provider config, `KernelSettings`-style
   contracts for provider selection). Needed before `agents` can do
   anything model-backed.
5. **`plugins`** (plugin loading) — depends on `core`; benefits from
   `events` existing first (plugins commonly want to hook lifecycle
   events). Fills the one named-but-unimplemented capability sitting in an
   already-reserved package.
6. **`agents`** (agent lifecycle) — depends on `providers`, `tools`,
   `memory`, `events`. The first subsystem that is a genuine consumer of
   everything built above.
7. **`workflow`** (workflow engine) — depends on `agents`, `tools`,
   `events`. Orchestrates the others; naturally last among the functional
   subsystems.

Security primitives and the remainder of Observability (tracing, metrics,
audit trail) aren't placed in this sequence because, per ADR-0002, their
package location is still an open architectural question — sequencing them
meaningfully requires that decision first.
