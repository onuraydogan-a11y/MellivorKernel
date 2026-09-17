# Changelog

All notable changes to Mellivor Kernel are documented in this file, per the
commitment in [ADR-0005](docs/adr/0005-versioning-strategy.md). Entries
start at `1.0.0` — no prior release is backfilled here; the pre-1.0 history
is recorded in [`RELEASE_NOTES_v0.5.0.md`](RELEASE_NOTES_v0.5.0.md) and
[`docs/architecture/roadmap.md`](docs/architecture/roadmap.md).

## [1.3.0] - 2026-09-17

Backward-compatible tool calling: a model may choose which kernel tools to
call, and the kernel executes them through its existing authorization and
pipeline path. See [ADR-0028](docs/adr/0028-provider-tool-calling-and-execution-tool-loop.md)
and [`RELEASE_NOTES_v1.3.0.md`](RELEASE_NOTES_v1.3.0.md).

### Added

- `providers.tool_calling`: SDK-free `ToolSpec`, `ToolCall`,
  `ToolResultBlock`, `ToolCallingError`, and the `assistant_message` /
  `tool_results_message` builders that define the provider-neutral message
  shape (string content, or `text` / `tool_use` / `tool_result` blocks).
- `execution.tool_loop.ToolCallLoop`: runs a model-with-tools conversation
  to a final answer. Every provider invocation and tool execution goes
  through `ExecutionEngine`; the offered tools are a mandatory allowlist;
  `ToolLoopOptions` carries `max_iterations` (default 8), `system`,
  `max_tokens` and a `before_tool_call` hook (default: allow). Refused
  calls are returned to the model as error results. Exhaustion is reported
  (`ToolLoopResult.exhausted`), not raised.
- Execution events `ToolCallRequested`, `ToolCallCompleted`,
  `ToolCallRejected`.
- `BaseTool.input_schema`: optional, non-abstract, default
  `{"type": "object"}`.
- `ClaudeProvider`: accepts `messages` (neutral shape) as an alternative to
  `prompt`, and `tools`; returns `tool_calls`. `supports_tool_calls=True`.
- `OpenAIProvider`: accepts `system` and `tools`, block-content messages;
  returns `tool_calls`. `supports_tool_calls=True`.
- `LocalProvider`: accepts `system` and `tools`, block-content messages;
  returns `tool_calls`. `supports_tool_calls` is opt-in via
  `ProviderConfiguration.extra["supports_tool_calls"]`.

### Changed

- A provider response that carries tool calls but no text no longer raises
  the provider's "no text content" error; it returns `text=""` with the
  calls. Only the previous error path is affected.
- `OpenAIProvider` and `LocalProvider` accept `messages` as any sequence,
  not only a `list`.
- Provider responses gain a `tool_calls` key (empty tuple when none).
  Callers that compared the whole response mapping for equality must
  include it.

### Compatibility

- The v1.2 public API remains unchanged: no abstract method added, no
  signature or type changed, nothing removed. Existing `{"prompt": ...}`
  and string-content `{"messages": ...}` callers behave as before.
- `GeminiProvider` is unchanged and does not declare tool-call support.
- Third-party providers that do not set `supports_tool_calls` are refused
  by `ToolCallLoop` before any request; they keep working everywhere else.

## [1.2.0] - 2026-09-01

Backward-compatible local-inference connectivity through the existing
provider abstraction. See [`RELEASE_NOTES_v1.2.0.md`](RELEASE_NOTES_v1.2.0.md)
and the [Sprint 33 release audit](docs/release/v1.2-release-audit.md).

### Added

- `LocalProvider`, an additive optional provider for synchronous text chat
  through a caller-managed OpenAI-compatible endpoint. The provider uses the
  `local` extra (`httpx>=0.28.1,<1`) and does not install, start, manage, or
  download a local-model runtime.

### Compatibility

- The v1.1 public API remains unchanged. `LocalProvider` implements the
  existing `BaseProvider` and `ProviderConfiguration` contracts without
  modifying existing provider behavior.
- Deterministic mocked integration covers the documented Chat Completions
  protocol subset. Compatibility with a specific Ollama, LM Studio, or vLLM
  installation is not claimed until that runtime is validated separately.

### Known limitations

- Kernel does not install or start local-model runtimes, manage runtime
  processes, or download models. The caller owns endpoint selection and the
  complete runtime lifecycle.
- Runtime-specific behavior and individual model builds were not certified in
  Sprint 32. Servers that differ from the validated protocol subset may
  require separate integration validation.

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
- The directly imported test dependency `httpx` is now declared in `dev`
  instead of being obtained accidentally through provider SDKs. It remains
  absent from base runtime dependencies and is owned at runtime by the
  `gemini` extra. CI continues to install all provider extras.

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
