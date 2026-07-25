# `security` subsystem spec

Status: Foundation (Sprint 15)

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
registry explicitly and resolves a secret only when needed.

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
