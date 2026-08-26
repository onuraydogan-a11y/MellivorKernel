# `security` subsystem spec

Status: Foundation (Sprint 15); first concrete `SecretProvider` backend
added (Sprint 28).

Public contract exported from `mellivor_kernel.security`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## Scope of this sprint

This spec defines the reusable security foundation that a future release can
build on. It deliberately does not implement authentication, OAuth, SSO,
RBAC, product-specific security policy, networking, or Mellivor One
features. The goal is to establish a kernel-owned contract surface for:

- security contracts
- secret abstraction
- secret provider interface
- secure configuration abstraction
- security policy abstraction
- audit contracts
- common security exceptions

Everything in this sprint is dependency-injected and remains structurally
separate from `execution`, `workflow`, `agents`, and `providers`.

## Public contracts

### `Secret`

An immutable dataclass holding a named secret value. The value is stored as
provided and the `repr()` intentionally redacts the literal secret so the
secret is never exposed by default logging or error messages.

### `SecretProvider`

A minimal resolve-by-name interface for secret retrieval. Implementations are
expected to perform any provider-specific lookup or retrieval logic, while the
kernel remains agnostic to how a secret is stored.

### `SecretProviderRegistry`

A tiny registry that resolves secrets through a list of registered providers.
This is intentionally small and dependency-injected: a consumer composes the
registry explicitly and resolves a secret only when needed. `resolve()`
tries each registered provider in order, catching `SecurityError` and
continuing to the next; every concrete `SecretProvider` must raise a
`SecurityError` subclass (never return `None` or raise a non-kernel
exception) for this fallback chaining to work.

### `EnvSecretProvider`

The first concrete `SecretProvider` implementation (Sprint 28) — read-only,
backed by the calling process's own environment variables, using only the
Python standard library (`os`, `re`): no new dependency, mandatory or
optional. See [ADR-0022](../adr/0022-env-secret-provider.md) for the full
design rationale.

```python
def __init__(self, prefix: str = "") -> None
def resolve(self, name: str) -> Secret
```

`prefix` is optional and defaults to no prefix (`name` is looked up
verbatim in `os.environ`); when set, every lookup uses
`os.environ[f"{prefix}{name}"]`. No caching — every `resolve()` call reads
the live environment, and no resolved value is retained on the instance.
Safe to call concurrently from multiple threads (no mutable instance state
beyond the immutable `prefix`).

Three distinct failure modes, each with its own exception type (all
`SecurityError` subclasses, added in this sprint):

- **`SecretNotFoundError`** — no environment variable with the resolved
  key is set.
- **`SecretValueError`** — the environment variable is set but its value
  fails `Secret`'s own validation (for example, empty).
- **`SecretConfigurationError`** — the lookup request itself is invalid: a
  blank `name`, or a `name`/`prefix` combination that does not resolve to
  a valid environment-variable identifier.

No exception message this provider raises ever includes the resolved
secret value — only the secret's `name` or the computed environment
variable key. No logging statements exist in this module, eliminating the
redact-in-logs risk surface entirely. No encryption at rest, no secret
rotation, and no built-in audit trail — see ADR-0022's "Security
limitations" for the full, explicit list.

### `SecurityPolicy`

A structural protocol for evaluating a security decision for a subject/action
pair. This keeps the kernel free of a concrete policy engine while still
allowing future consumers to supply their own policy implementation.

### `SecurityDecision`

A frozen dataclass describing the outcome of a policy evaluation.

### `SecureConfiguration`

A structural protocol for consumers that need both plain configuration values
and secret-backed values without coupling their application code to any one
secret provider implementation.

### `AuditRecord`

A frozen dataclass describing a security-relevant audit event.

### `AuditSink`

A structural protocol for recording audit events. Implementations can emit to
logs, memory, or a product-specific audit store without asking the kernel to
choose one for them.

## Exceptions

`security.exceptions.SecurityError` is the base class for every security
exception in the subsystem. `SecureConfigurationError` is the dedicated error
raised for invalid secure-configuration lookup or validation behavior.

Added in Sprint 28, backend-agnostic (any current or future concrete
`SecretProvider` may raise them, not only `EnvSecretProvider`):

- `SecretNotFoundError` — a requested secret does not exist in the
  provider's source.
- `SecretValueError` — a secret's resolved value fails validation.
- `SecretConfigurationError` — a secret lookup request is itself invalid,
  independent of whether the secret exists.

All three subclass `SecurityError`.

## Architectural rule

This sprint introduces a new top-level package, `security/`, and keeps it
business-agnostic. The package does not add product policy, user identity,
or application-level authorization logic. It only provides the reusable,
compile-time-visible contracts and runtime primitives required for a future
product or subsystem to build those capabilities safely.

## v1.0 scope note (Sprint 25 Public API Freeze Audit)

`AuditRecord`/`AuditSink` are proven by internal usage —
`authorization.AuthorizationEngine` has recorded every grant/deny
decision through a configured `AuditSink` since Sprint 17. `Secret`/
`SecretProvider`/`SecretProviderRegistry` and the `SecurityPolicy`/
`SecureConfiguration` protocols have no production consumer anywhere in
the kernel; they are exercised only by structural fakes in this
package's own tests. This was already the explicit, accepted premise of
this sprint's own scope ("not yet consumed by any other subsystem") and
of [ADR-0019](../adr/0019-release-readiness-and-scope-lock.md)'s
"bring your own backend" classification of this responsibility. Ratified
as intentional, stable `1.0.0` scope: these contracts exist for a future
concrete backend to implement against, not because anything in the
kernel itself calls them yet. No code change results from this
ratification.
