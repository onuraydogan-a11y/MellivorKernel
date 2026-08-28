# Changelog

All notable changes to Mellivor Kernel are documented in this file, per the
commitment in [ADR-0005](docs/adr/0005-versioning-strategy.md). Entries
start at `1.0.0` — no prior release is backfilled here; the pre-1.0 history
is recorded in [`RELEASE_NOTES_v0.5.0.md`](RELEASE_NOTES_v0.5.0.md) and
[`docs/architecture/roadmap.md`](docs/architecture/roadmap.md).

## [1.1.0] - 2026-08-28

Backward-compatible expansion of the stable v1 API. See
[`RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md) and the
[Sprint 31 release audit](docs/release/v1.1-release-audit.md).

### Added

- `SQLiteMemoryStore`, a durable standard-library SQLite implementation of
  the unchanged `MemoryStore` contract.
- `EnvSecretProvider` and backend-agnostic missing/value/configuration secret
  errors, all compatible `SecurityError` subclasses.
- `GeminiProvider` behind the optional `gemini` extra.
- `WorkflowExecutionOptions`, `RequestResolver`, `Clock`, `SystemClock`, and
  the optional keyword-only `WorkflowEngine.run(..., options=...)` extension
  for dynamic requests, explicit parallel groups, and `not_before` guards.

### Changed

- Provider dependency bounds now declare supported major versions:
  `anthropic>=0.40,<1`, `openai>=1.0,<3`, and `google-genai>=2.0,<3`.
- CI installs all provider extras. The directly imported test dependency
  `httpx` is declared in `dev`; it remains absent from base runtime
  dependencies and is owned at runtime by the `gemini` extra.

### Compatibility correction

- ADR-0025 supersedes ADR-0024's direct additions to `WorkflowStep`.
  `WorkflowStep` is identical to v1.0 in constructor, annotations, fields,
  defaults, dataclass behavior, representation, equality/hash, serialization,
  subclassing, and static typing.

### Breaking changes

- None.

### Known limitations

- A single `SQLiteMemoryStore` connection must not be shared across workflow
  parallel branches without external synchronization. Use per-branch stores
  or another thread-safe `MemoryStore`.
- Scheduling is an eligibility check only. Kernel owns no daemon, polling
  loop, persistent scheduler, queue, or background worker.
- Gemini remains synchronous plain-text Developer API support; streaming,
  tools, multimodal input, Vertex AI authentication, and batch execution are
  intentionally deferred.

## [1.0.0] - 2026-07-28

First stable release. See
[`RELEASE_NOTES_v1.0.0.md`](RELEASE_NOTES_v1.0.0.md) for the full release
record and [ADR-0020](docs/adr/0020-release-decision-v1.0.md) for the
governance decision.

### Added

- Formal `1.0.0` compatibility promise, per ADR-0020, covering every
  responsibility in [ADR-0002](docs/adr/0002-ai-enterprise-kernel-scope-and-subsystems.md)
  as classified by [ADR-0019](docs/adr/0019-release-readiness-and-scope-lock.md):
  `core`, `config`, `tools`, `providers` (`BaseProvider`, `ClaudeProvider`,
  `OpenAIProvider`), `bootstrap`, `execution`, `authorization`, `events`,
  `memory`, `workflow`, `agents` (baseline), `security`, `observability`
  (both "bring your own backend"), `plugins`, `plugin_sdk`,
  `plugins_builtin`, `plugin_discovery`, and `ai_engine`.

### Changed

- Versioning policy: the SemVer post-1.0 discipline and deprecation policy
  defined in ADR-0005 are now binding. Breaking changes to any public
  contract require a MAJOR version bump.

### Breaking changes

- None. `1.0.0` is the first stable line drawn under the existing,
  already-shipped public API; nothing was removed or changed to reach it.

### Deferred

- Not part of this release's compatibility promise. See ADR-0019 and
  `docs/release/v1.0-release-checklist.md` for the full, classified list:
  dynamic/parallel/scheduled workflow execution, a persistent `MemoryStore`,
  additional providers, a concrete `SecretProvider` backend (all
  `Deferred to v1.1`); richer agent capability, embeddings/vector/RAG,
  distributed event delivery, plugin marketplace/sandboxing/remote plugins,
  a concrete metrics/tracing backend, and authentication/OAuth/SSO/RBAC/
  encryption-at-rest (all `Future research`).
