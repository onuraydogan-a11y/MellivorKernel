# Mellivor Kernel v1.1.0

Commit: this release commit (`release(v1.1): prepare Mellivor Kernel 1.1.0`)

Branch: `main`

Tag: `v1.1.0` — to be applied manually after Product Owner approval.

## Summary

Mellivor Kernel 1.1.0 completes the four capabilities explicitly deferred
from v1.0: durable SQLite memory, an environment-backed secret provider,
Gemini support, and dynamic/parallel/scheduled workflow execution. It is a
backward-compatible MINOR release under ADR-0005.

The original Sprint 30 design in ADR-0024 altered the frozen `WorkflowStep`
dataclass and was rejected by the first release-gate audit. ADR-0025
supersedes that surface, restores `WorkflowStep` exactly, and places the new
behavior in additive per-run `WorkflowExecutionOptions`.

## Public additions

- `memory.SQLiteMemoryStore`
- `security.EnvSecretProvider`, `SecretNotFoundError`, `SecretValueError`,
  `SecretConfigurationError`
- `providers.gemini.GeminiProvider` and its adapter-specific errors
- `workflow.WorkflowExecutionOptions`, `RequestResolver`, `Clock`,
  `SystemClock`
- Optional keyword-only workflow engine construction/run parameters

No v1.0 public API was removed, renamed, reordered, or changed in type or
meaning. In particular, `WorkflowStep.request` remains required and statically
typed as `ExecutionRequest`.

## Dependencies

The base package still has no runtime dependency. Provider SDKs remain extras:

- `anthropic>=0.40,<1`
- `openai>=1.0,<3`
- `google-genai>=2.0,<3` and `httpx>=0.28.1,<1` for `gemini`

CI drift came from tests importing HTTPX directly while relying on the
provider SDKs to supply it transitively. Unbounded provider major versions
later migrated toward HTTPX 2. Commit `6b17370` permanently corrected the
model by declaring and bounding HTTPX directly in `dev` and `gemini`, and by
bounding the supported provider SDK majors; CI already installed every
provider extra.

## Upgrade from v1.0.0

```bash
pip install --upgrade mellivor-kernel==1.1.0
```

No consumer migration is required. Add `[gemini]` only when using Gemini.
Supply `WorkflowExecutionOptions` only when opting into new workflow behavior.

## Known limitations and deferred work

- Do not share one `SQLiteMemoryStore` connection across parallel workflow
  branches without external synchronization.
- `not_before` is an eligibility guard, not a durable scheduler; the kernel
  owns no daemon, polling loop, queue, or background worker.
- Gemini is synchronous plain-text Developer API support only.
- Richer agent capability, vector/RAG memory, distributed events, plugin
  marketplace/sandboxing, telemetry backends, and authentication/RBAC remain
  future work. No post-v1.1 capability is included in this release.

## Verification

Sprint 31 verified 857 tests, Ruff lint/format, strict MyPy, wheel and sdist
builds, isolated artifact installs, dependency metadata, and GitHub Actions
run #41 on Python 3.12 and 3.13. See the complete
[v1.1 release audit](docs/release/v1.1-release-audit.md).
