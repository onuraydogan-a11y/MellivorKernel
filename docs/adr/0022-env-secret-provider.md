# 0022. Concrete `SecretProvider` backend: `EnvSecretProvider`

Status: Accepted
Date: 2026-08-26

## Context

[ADR-0012](0012-security-foundation.md) shipped `security` with the
`SecretProvider` structural `Protocol` and `SecretProviderRegistry`, but
**no concrete implementation** — every existing exercise of the contract
is a structural fake in `tests/security/test_foundation.py`
(`ExampleSecretProvider`), never a real secret source. Both
[ADR-0019](0019-release-readiness-and-scope-lock.md) and
[ADR-0020](0020-release-decision-v1.0.md) classify "a concrete
`SecretProvider` backend" as `Deferred to v1.1`, scoped by name, with no
further design gate required before scheduling it — the same "prove an
existing contract with a first real implementation" shape as `providers`
(`ClaudeProvider`) and `memory`
([`SQLiteMemoryStore`](0021-persistent-memory-sqlite-store.md), Sprint
27, this same v1.1 line).

This is Sprint 28, per direct Product-Owner instruction: "Add the first
production-usable concrete backend for the existing `SecretProvider`
abstraction... prove that the existing v1.0 security abstraction
supports a real secret source without changing the public contract."

**Architecture review finding.** Before writing this ADR, the full
`security` subsystem was inspected: `secrets.py` (`Secret`,
`SecretProvider`, `SecretProviderRegistry`), `exceptions.py`
(`SecurityError`, `SecureConfigurationError`), `contracts.py`
(`SecurityPolicy`, `SecureConfiguration`), `policy.py`, `audit.py`, and
`tests/security/test_foundation.py`, together with ADR-0012, ADR-0019,
and `docs/specs/security.md`. Three properties of the existing contract
matter directly to this sprint's design and were confirmed, not assumed:

1. `SecretProvider` is a two-member structural `Protocol`: exactly
   `resolve(name: str) -> Secret`. No `set`/`delete`/`list` — read-only
   by construction, not by a convention this sprint has to invent.
2. `Secret.__post_init__` already rejects a blank `name` or an empty
   `value`, raising `SecurityError` — a concrete provider **cannot**
   construct a `Secret` around an empty value even if it wanted to; this
   constraint already exists in the frozen v1.0 contract, not something
   this sprint adds.
3. `SecretProviderRegistry.resolve()` iterates its registered providers
   and `except SecurityError: continue`s past a failing one, raising only
   if every provider fails. This fixes an implicit but real behavioral
   requirement on any concrete `SecretProvider`: a lookup failure **must**
   raise a `SecurityError` subclass (not return `None`, not raise
   `KeyError` or any other exception type) for the registry's fallback
   chaining to work as designed.

No architectural conflict was found: `SecretProvider` supports a real,
concrete, read-only backend with **zero change** to `SecretProvider`,
`Secret`, `SecretProviderRegistry`, `SecurityPolicy`, `SecureConfiguration`,
`SecurityDecision`, `AuditRecord`, `AuditSink`, or the two existing
exceptions. This ADR proceeds on that basis; per this sprint's own
instruction, had a conflict been found, this ADR would stop and report it
instead.

## Decision

**A new module, `src/mellivor_kernel/security/env_secret_provider.py`,
adds `EnvSecretProvider`** — a `SecretProvider` implementation that
resolves secrets from the calling process's own environment variables.
Exported from `mellivor_kernel.security.__all__` alongside the seven
existing names; nothing already exported changes shape or behavior.

**Backend choice and rationale.** Per the sprint's own instruction --
"select the backend based on architectural fit, portability, security,
dependency cost, and production usefulness... prefer a backend that does
not create unnecessary infrastructure coupling" -- three options were
weighed (see "Alternatives considered"). The process environment was
chosen because:

- **Architectural fit.** `SecretProvider.resolve(name) -> Secret` is
  already shaped exactly like an environment lookup: a name in, a value
  out, read-only, no listing/enumeration in the contract to satisfy.
- **Portability.** `os.environ` behaves identically across every
  platform and deployment target the kernel already supports (no OS- or
  cloud-specific API), and is standard library -- **zero new dependency**,
  mandatory or optional, matching the pattern already set for
  `SQLiteMemoryStore` (ADR-0021).
- **Security.** No network call, no credential-to-fetch-credentials
  problem (a vault-backed provider needs its own bootstrap secret to
  authenticate to the vault -- environment variables are the substrate
  every other secret-delivery mechanism, including a vault agent's own
  sidecar injection, ultimately lands secrets into for a process to read).
- **Production usefulness.** Environment-variable-injected secrets are
  the de facto standard for every mainstream deployment target Mellivor
  products already target -- containers (Docker/Kubernetes `env`/
  `envFrom`), CI/CD systems, and process managers all inject secrets this
  way. This is not a toy backend; it is what most production deployments
  already do today, manually, without a kernel-level abstraction around
  it.
- **No infrastructure coupling.** Introduces no service to run, no
  credential of its own to manage, no client library, no network
  dependency.

**Source of secrets.** The calling process's own environment
(`os.environ`), read directly -- not a `.env` file, not another
process's environment, not a container-orchestration secret API. An
optional constructor `prefix: str = ""` namespaces the lookup
(`resolve("api_key")` reads `os.environ[f"{prefix}api_key"]`), a generic,
opt-in convenience (defaults to no prefix, i.e. direct passthrough) --
not a product-specific naming convention, since the kernel does not
choose or impose any specific prefix value.

**Lookup semantics.** `resolve(name)`:

1. Rejects a blank `name` immediately (`SecretConfigurationError`),
   before touching the environment.
2. Computes `env_key = f"{prefix}{name}"` and validates it matches
   `^[A-Za-z_][A-Za-z0-9_]*$` -- the portable environment-variable
   identifier pattern -- raising `SecretConfigurationError` if not. This
   is a real, not contrived, "malformed configuration" case: a `prefix`
   or `name` containing e.g. `=` or whitespace would silently never
   match any real environment variable, which is worse than failing
   loudly at the point of misconfiguration.
3. If `env_key` is not present in `os.environ`, raises
   `SecretNotFoundError` -- the "missing variable" case.
4. If present, constructs `Secret(name=name, value=os.environ[env_key])`.
   `Secret.__post_init__` itself rejects an empty value; that
   `SecurityError` is caught and re-raised as `SecretValueError` with
   the environment variable's name (never its value) added for context --
   the "present but empty value" case, distinguished from "missing"
   both by exception type and by message.
5. Otherwise returns the constructed `Secret`.

**Missing-secret behavior:** `SecretNotFoundError` (see above) -- a
`SecurityError` subclass, so `SecretProviderRegistry.resolve()`'s
existing `except SecurityError: continue` correctly falls through to the
next registered provider with no change to the registry.

**Validation behavior:** three distinct, ordered checks (blank name →
malformed resolved key → missing → empty value), each with its own
exception type and a message naming the environment variable key
involved (never the secret's value).

**Error translation:** every failure mode raises a `security`-subsystem
exception (`SecretConfigurationError`, `SecretNotFoundError`, or
`SecretValueError`, all `SecurityError` subclasses) -- no raw
`KeyError`, `ValueError`, or any non-kernel exception ever crosses
`resolve()`'s boundary, per [ADR-0004](0004-public-api-philosophy.md)'s
"errors are translated at the boundary," the same discipline `providers`
already applies to vendor SDK exceptions and `SQLiteMemoryStore` (ADR-
0021) applies to `sqlite3` exceptions.

**Lifecycle:** `EnvSecretProvider()` takes no required argument and holds
no resource to open or close -- construction is instantaneous, and there
is nothing to release. No `__enter__`/`__exit__`, unlike
`SQLiteMemoryStore`; there is no file handle or connection here.

**Caching behavior: none, deliberately.** Every `resolve()` call reads
`os.environ` fresh. No value is cached, memoized, or retained on the
instance after `resolve()` returns. Two reasons: (1) determinism -- a
cache could return a stale value if the environment changes during a
process's life (e.g. a test fixture, or a long-running process whose
supervisor updates its environment); reading live avoids that entire
class of bug. (2) security -- retaining resolved secret values in the
provider's own instance state would be a second place they exist in
memory beyond the `Secret` object already returned to the caller, an
unnecessary expansion of exposure for no benefit `os.environ` doesn't
already provide "for free" as the actual, single source of truth.

**Concurrency behavior:** `EnvSecretProvider` holds no mutable instance
state beyond the immutable `prefix` string set at construction; `resolve()`
performs no writes anywhere. Safe to call concurrently from multiple
threads with no internal locking -- `os.environ` reads are safe under
CPython's GIL, and this class adds no shared mutable state on top of it.

**Mutation support:** none, and none is added. `EnvSecretProvider`
exposes only `resolve()` -- the exact `SecretProvider` Protocol surface,
nothing more. Read-only is not a convention this class follows; it is
the only thing the class's public surface is capable of, matching
`SecretProvider` itself having no write member to implement.

**Secret exposure boundaries:** the resolved value is placed into
exactly one object -- the returned `Secret`, whose `__repr__` is already
redacted by the existing contract (ADR-0012). No secret value is ever
interpolated into an exception message, a log line, a docstring, or any
diagnostic output this provider produces; every message this module
raises names only the secret's `name` or the resolved environment
variable's `env_key`, never `os.environ[env_key]`'s contents. This was
verified line-by-line while writing `resolve()` -- there is exactly one
place the raw value is read (`os.environ[env_key]`) and exactly one place
it is used (passed to `Secret(...)`), with no intermediate f-string or
log call touching it.

**Logging/redaction requirements:** `EnvSecretProvider` contains **no
logging statements at all** -- a deliberate choice to eliminate the
redact-in-logs risk surface entirely rather than attempt to log safely
around it. There is nothing this module needs to log: `resolve()` either
returns a `Secret` or raises a caller-visible exception, and the caller
(or an `AuditSink`, wired separately -- see "Consequences") owns any
decision to record that outcome.

**Environment/process isolation considerations:** this provider reads
only the *calling process's own* environment, populated however the
process was launched (shell export, container `env`/`envFrom`, CI
secret injection, a supervisor's process definition). It does not read
`.env` files, does not read another process's or container's
environment, and does not perform any cross-process or
cross-namespace secret sourcing. In a deployment where one process hosts
multiple tenants or consumers, all share the same process environment --
this is an existing property of `os.environ` itself, not something this
provider introduces or can scope down; a consumer with a multi-tenant
isolation requirement needs a different backend (out of this sprint's
scope, and likely `Future research` per ADR-0019's "concrete `SecretProvider`
backend" being the full extent of what v1.1 committed to).

**Security limitations**, stated plainly, not hidden behind "production-
grade" framing:

- No encryption at rest -- environment variables are held in the OS
  process table in plaintext and are typically visible to the same user
  (or root/Administrator) via OS-level process inspection
  (`/proc/<pid>/environ` on Linux, `Process Explorer`/`wmic` on Windows).
  This is an inherent property of the environment-variable delivery
  mechanism, not a gap this provider could close without becoming a
  different kind of backend entirely.
- No secret rotation -- a `EnvSecretProvider` instance always reads the
  live environment (no caching, per above), so a value changed in the
  environment *is* picked up on the next `resolve()` call, but nothing in
  this provider rotates, expires, or invalidates a secret -- that
  remains entirely the deployment platform's responsibility.
- No audit trail built into the provider itself -- if a consumer needs
  every `resolve()` call recorded, they compose an `AuditSink`
  themselves around the call site (`SecretProviderRegistry` also does
  not do this on its own). This mirrors `authorization.AuthorizationEngine`
  being the component that wires `AuditSink`, not `security` itself.
- Environment variables are inherited by child processes by default
  unless the caller explicitly scrubs them before spawning one -- an
  operational concern for the consuming application, out of scope for a
  kernel-level provider.
- No secret-existence enumeration -- `SecretProvider` has no `list()`
  member and this provider adds none; a caller cannot ask "what secrets
  are available," only resolve one they already know the name of.

**Test strategy:** `tests/security/test_env_secret_provider.py` covers
protocol conformance (`isinstance(EnvSecretProvider(), SecretProvider)`),
successful resolution, the three distinct failure modes (missing /
present-but-empty / malformed name or prefix) each asserted by exception
type and message content, deterministic repeated lookup, isolation
between keys (resolving one name never returns or is affected by
another), no accidental mutation of `os.environ` by `resolve()` itself,
redaction (the resolved value never appears in `repr()`/`str()` of the
returned `Secret` or in any raised exception's message), compatibility
with `SecretProviderRegistry` (a real fallback chain: `EnvSecretProvider`
first, missing there, falls through to a second in-test provider), and
the `prefix` namespacing behavior. `pytest`'s `monkeypatch.setenv`/
`delenv` fixtures set up and tear down the process environment per test
-- no test reads or depends on any variable already present in the host
environment, keeping every test isolated and deterministic regardless of
where `pytest` runs.

**Compatibility guarantees:** no change to `SecretProvider`, `Secret`,
`SecretProviderRegistry`, `SecurityPolicy`, `SecureConfiguration`,
`SecurityDecision`, `AuditRecord`, `AuditSink`, `SecurityError`, or
`SecureConfigurationError` -- verified by the full pre-existing test
suite (745 tests as of Sprint 27) passing unmodified.
`mellivor_kernel.security.__all__` gains four names --
`EnvSecretProvider`, `SecretConfigurationError`, `SecretNotFoundError`,
`SecretValueError` -- a MINOR-compatible addition per
[ADR-0005](0005-versioning-strategy.md).

## Alternatives considered

- **A file-backed provider** (reads secrets from a mounted file per
  name, e.g. Kubernetes/Docker secret volumes). Rejected for this
  sprint, not permanently: real production usefulness (this is exactly
  how orchestrators mount secrets), but it introduces filesystem-path
  ownership questions (one file per secret? one directory, one file per
  name inside it?) that mirror `SQLiteMemoryStore`'s "storage ownership"
  design work already done in ADR-0021, without adding a materially
  different lesson about the `SecretProvider` contract itself. The
  environment-variable backend proves the identical contract point --
  "a real, external secret source satisfies `SecretProvider` unmodified"
  -- with a strictly smaller design surface, matching the sprint's
  instruction to find "the smallest concrete backend that can
  demonstrate the abstraction correctly." A file-backed provider remains
  a reasonable second concrete implementation later, the same "prove it
  twice" precedent `providers` and `memory` both established.
- **A cloud-provider secret manager client** (AWS Secrets Manager, GCP
  Secret Manager, Azure Key Vault, HashiCorp Vault). Rejected outright
  for this sprint: explicitly excluded by this sprint's own scope ("no
  cloud-specific control planes"), and would add a real network
  dependency, a new third-party SDK, and a bootstrap-credential problem
  (the client itself needs credentials to authenticate, which begs the
  question this sprint is trying to answer). A legitimate future
  candidate once a concrete product need names a specific vendor --
  each would need its own ADR, following this one's precedent, not a
  kernel-chosen default.
- **A `.env`-file-parsing provider** (reads a `KEY=value` file into
  memory). Rejected: `.env` file parsing has no single standard format
  (quoting, escaping, comments, multiline values all vary by
  implementation), which is exactly the "malformed configuration"
  surface area this sprint is supposed to minimize, not invent from
  scratch. Loading a `.env` file into the *actual* process environment
  before the kernel starts (e.g. via a `dotenv`-style tool run by the
  consumer, entirely outside this kernel) and then reading it through
  `EnvSecretProvider` gets the same result with zero new parsing code in
  the kernel.
- **Caching resolved secrets on the instance.** Considered and rejected;
  see "Caching behavior" above -- staleness risk and unnecessary
  in-memory exposure, for no measured performance need (`os.environ`
  access is a fast, in-process dict lookup with no I/O).
- **Silently falling back to an empty or placeholder `Secret`** when a
  variable is missing, rather than raising. Rejected outright: this is
  exactly the "no implicit insecure fallback" the sprint's Phase 2
  instructions forbid, and `Secret.__post_init__` would reject an empty
  value anyway -- there is no valid placeholder to fall back to within
  the existing contract.
- **Reusing the existing `SecureConfigurationError`** for the new
  "malformed name/prefix" case, instead of a new
  `SecretConfigurationError`. Rejected: `SecureConfigurationError`'s
  documented scope is the `SecureConfiguration` protocol (`get_secret`/
  `get_value`), a different contract this sprint does not implement or
  touch; reusing it here would blur two unrelated failure domains under
  one exception type.
- **Defining `EnvSecretProvider`'s exceptions locally in its own module**
  (the pattern `ClaudeProvider`/`OpenAIProvider` use for their
  vendor-specific exceptions). Rejected: those providers' exceptions
  (`ClaudeAuthenticationError`, `ClaudeTimeoutError`, ...) are genuinely
  vendor-specific failure modes a *different* provider wouldn't share.
  `SecretNotFoundError`/`SecretValueError`/`SecretConfigurationError`
  are backend-agnostic categories any future concrete `SecretProvider`
  (a file-backed or vault-backed one) would also want to raise --
  placed in the shared `security/exceptions.py` so a future backend
  reuses them rather than inventing parallel per-backend equivalents,
  mirroring how `MemoryError` is shared across both `MemoryStore`
  backends rather than split per-implementation.
- **Exporting `EnvSecretProvider` only from its own module**, not from
  `security.__all__` (the `providers.claude`/`providers.openai`
  pattern). Rejected: that pattern exists specifically to avoid an eager
  import of an optional, heavyweight third-party SDK when a consumer
  imports `mellivor_kernel.providers` and never uses that vendor.
  `EnvSecretProvider` has no third-party dependency at all (standard
  library only) -- there is no import cost to avoid, so the applicable
  precedent is `SQLiteMemoryStore`'s (ADR-0021): zero-dependency
  concrete implementations are exported directly.

## Consequences

- `mellivor_kernel.security.__all__` gains four names --
  `EnvSecretProvider`, `SecretConfigurationError`, `SecretNotFoundError`,
  `SecretValueError`. Seven existing names are unchanged.
- `security` continues to depend only on `core` (`KernelError`) plus,
  now, the standard-library `os` and `re` modules -- no new third-party
  dependency, no new `pyproject.toml` optional-dependency group, no CI
  change.
- A consuming product (Mellivor One, Mellivor AI Security) now has a
  supported, zero-extra-dependency way to resolve real secrets through
  `SecretProviderRegistry`, composable with any other `SecretProvider`
  they supply themselves -- the registry's existing fallback-chaining
  behavior is unchanged and works with `EnvSecretProvider` with no
  special-casing.
- Nothing in the kernel's own code (`execution`, `authorization`,
  `ai_engine`) is changed to consume `EnvSecretProvider` automatically --
  matching `security`'s existing "dependency-injected, not wired by
  default" posture (ADR-0012) and this sprint's own instruction not to
  introduce product-specific secret handling.
- Sprint 29 (Gemini provider) is a structurally different kind of sprint
  -- a second/third `BaseProvider` implementation, not a `security`
  change -- and is unaffected by this ADR.
- This ADR neither promises nor precludes a second concrete
  `SecretProvider` implementation (file-backed, vault-backed) later; per
  ADR-0019, any such addition is its own scoped decision, not implied by
  this one.
