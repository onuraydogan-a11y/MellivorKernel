# 0023. Third concrete provider: `GeminiProvider`

Status: Accepted
Date: 2026-08-26

## Context

`providers` has two concrete implementations of `BaseProvider` --
`ClaudeProvider` (Sprint 10, a flat prompt string) and `OpenAIProvider`
(Sprint 23, a multi-turn message list) -- each proving `BaseProvider`'s
generic `invoke(request: Mapping) -> Mapping` contract generalizes to a
genuinely different request shape, with no ADR needed for either (Sprint
10's own precedent: an additional concrete implementation of an
already-stable contract is not an architecturally significant change).
Both [ADR-0019](0019-release-readiness-and-scope-lock.md) and
[ADR-0020](0020-release-decision-v1.0.md) classify "additional concrete
providers (Gemini, local models)" as `Deferred to v1.1`.

This is Sprint 29, per direct Product-Owner instruction: "Add Google
Gemini as an additional concrete AI provider behind the existing Mellivor
Kernel provider abstraction... prove that the provider architecture
remains vendor-neutral beyond the existing Claude and OpenAI
implementations." This sprint's own instructions require an ADR
regardless of the Sprint 10 precedent, given the added weight of a
client-library selection decision -- so this ADR exists for that reason,
not because `BaseProvider` itself needed to change.

**Architecture review finding.** Before writing this ADR, `providers/base.py`
(`BaseProvider`), `capabilities.py` (`ProviderCapabilities`),
`configuration.py` (`ProviderConfiguration`), `exceptions.py`,
`health.py`, `registry.py`, `factory.py`, and both concrete providers
(`claude.py`, `openai.py`) were inspected in full, together with
`docs/specs/providers.md`'s full history (including the Sprint 25 Public
API Freeze Audit's "v1.0 contract ratification"). Confirmed:

1. `BaseProvider` is a four-member `ABC`: `name`, `capabilities`,
   `check_health()`, `invoke(request: Mapping) -> Mapping`. `invoke`'s
   request/response shape is a deliberately generic `Mapping[str, object]`
   -- no formal cross-provider schema exists or is expected; each
   concrete provider defines its own shape, a design already exercised
   twice.
2. `ProviderCapabilities`'s flags (`supports_streaming`,
   `supports_tool_calls`, `supports_vision`, `supports_embeddings`,
   `max_context_tokens`) are "descriptive metadata only... they do not
   yet correspond to dedicated abstract methods on `BaseProvider`" --
   ratified as accurate, not aspirational, by the Sprint 25 audit. Both
   existing providers report `ProviderCapabilities()` (every flag at its
   `False`/`None` default). Nothing in the contract obligates a provider
   claiming any capability to implement it.
3. Every credential field is required explicitly from
   `ProviderConfiguration` and must never fall back to an SDK's own
   environment-variable lookup -- a documented, binding "convention for
   future providers" in `docs/specs/providers.md`, not merely a
   suggestion.
4. The Sprint 25 audit ratified a specific five-class exception shape
   (`<Vendor>ProviderError` base, plus `Authentication`/`Timeout`/
   `Connection`/`Response` subclasses) as "the stable `1.0.0` contract...
   any future provider is expected to define the same five-class shape."

No architectural conflict was found: `BaseProvider` supports a third,
structurally distinct request/response shape with **zero change** to
`BaseProvider`, `ProviderCapabilities`, `ProviderConfiguration`,
`ProviderHealthCheck`, `ProviderRegistry`, `ProviderFactory`,
`ProviderError`, `ProviderConfigurationError`, or
`ProviderRegistrationError`. This ADR proceeds on that basis; per this
sprint's own instruction, had a conflict been found, this ADR would stop
and report it instead.

## Decision

**A new module, `src/mellivor_kernel/providers/gemini.py`, adds
`GeminiProvider`** -- a `BaseProvider` implementation backed by the
Gemini Developer API. **Not exported from
`mellivor_kernel.providers.__all__`** -- imported explicitly from
`mellivor_kernel.providers.gemini`, the same separation `ClaudeProvider`/
`OpenAIProvider` already keep from the base `providers` package, for the
same reason: this module is the only one in the repository that imports
the vendor SDK, so a consumer who never uses Gemini never needs it
installed.

### Client/library choice

**`google-genai`** (import path `google.genai`), Google's current,
actively maintained, unified SDK for the Gemini Developer API. Verified
directly (both by web research and by installing and introspecting the
package locally against version `2.20.0`) rather than assumed:

- **Dependency stability.** The older `google-generativeai` package is
  fully deprecated -- "all support... has ended and will no longer
  receive updates or bug fixes" as of November 30, 2025 -- with Google's
  own documentation directing developers to `google-genai`. Selecting
  the deprecated package would violate this sprint's "do not select an
  approach merely because it is easiest to code" instruction in the
  opposite direction: it would be selecting a *worse-maintained* option
  for no benefit. `google-genai` is Google's own stated, current
  recommendation, in General Availability, used in all official
  documentation and examples.
- **Testability.** `google-genai`'s `Client` is a plain, injectable
  object (`client = genai.Client(...)`); `client.models.generate_content(...)`
  is a single method call this sprint fakes the same way
  `ClaudeProvider`/`OpenAIProvider` already fake `client.messages.create`/
  `client.chat.completions.create` -- no different testing shape.
- **API surface.** A single `models.generate_content()` call covers this
  sprint's synchronous, plain-text scope with no lower-level surface
  needed.
- **Vendor lock-in.** No greater than `anthropic`/`openai` already
  represent -- `google-genai` is isolated to this one module, the same
  way the other two vendor SDKs are, so switching or adding a fourth
  provider later requires no change anywhere else.
- **Consistency with existing implementations.** `google-genai` is a
  synchronous-capable, `httpx`-based HTTP client library, structurally
  the same shape as `anthropic`/`openai`'s own SDKs (both also
  `httpx`-based) -- no new HTTP stack pattern is introduced.
- **Compatibility with the kernel's abstractions.** Confirmed directly:
  `Client(api_key=..., http_options=...)` supports explicit credential
  injection with no environment-variable fallback required, matching
  this sprint's binding "convention for future providers."

**Direct HTTP was rejected**: it would mean hand-rolling request
serialization, response parsing, retry, and auth-header handling that
`google-genai` already implements and Google maintains -- pure
reimplementation cost for no isolation benefit `google-genai` doesn't
already provide (it is already isolated to this one module, exactly like
`anthropic`/`openai`). The (now-deprecated) `google-generativeai` package
was rejected outright per the dependency-stability point above.

**New optional dependency:** `google-genai>=2.0` (`pip install
mellivor-kernel[gemini]`). `providers/gemini.py` is the only module
anywhere in this repository that imports `google.genai` -- no other
kernel code imports this module or the SDK, mirroring `claude.py`'s/
`openai.py`'s isolation exactly. The lower bound is `>=2.0`, not the
looser `>=1.0`-style bound `anthropic`/`openai` use, because
`google-genai` underwent a real 1.x-to-2.x transition; every field name
and method signature this ADR and the implementation depend on was
verified against `2.20.0` specifically, and pinning below `2.0` would
risk silently accepting an incompatible major version.

### Supported Gemini API surface

Exactly one operation: `client.models.generate_content(model, contents,
config)`, synchronous, non-streaming, plain text in and out. No chat
session object, no file/image/video input, no embeddings endpoint, no
batch API, no live/bidirectional API, no code execution or
Google-Search-grounding tools.

### Model configuration

`configuration.default_model` is required and passed as `model` on every
`generate_content()` call (e.g. `"gemini-2.0-flash-001"`) -- no
model-listing or model-discovery call is made; the kernel does not
validate the model identifier itself, exactly as neither `ClaudeProvider`
nor `OpenAIProvider` does.

### Credential handling

`configuration.api_key` is required and passed explicitly as
`genai.Client(api_key=...)`. **Does not** fall back to the SDK's own
`GOOGLE_API_KEY`/`GEMINI_API_KEY` environment-variable resolution --
`GeminiProvider` raises `ProviderConfigurationError` at construction if
`api_key` is unset, the same binding convention `ClaudeProvider`/
`OpenAIProvider` already follow. `configuration.base_url` (if set) and
`configuration.timeout_seconds`/`max_retries` are passed through via
`genai.Client(http_options=types.HttpOptions(...))` -- confirmed by
direct introspection to be the only place `Client` accepts them (unlike
`anthropic.Anthropic`/`openai.OpenAI`, which take `base_url`/`timeout`/
`max_retries` as direct constructor kwargs, `google-genai` nests all
three under one `http_options` object; a real, verified structural
difference between this SDK and the other two, not an inconsistency this
provider introduces).

Only the **Gemini Developer API** authentication path (`api_key`) is
supported -- not Vertex AI's project/location/`Credentials`-based
authentication (`Client(vertexai=True, project=..., location=...)`),
which would require GCP-specific configuration fields
`ProviderConfiguration` does not have and this sprint's scope explicitly
excludes ("no cloud-specific control planes").

**Verified, real limitation to document, not silently omit:** the
`google-genai` SDK has a documented issue (tracked upstream) where its
internal HTTP layer can override an explicitly configured `httpx` client
timeout with `None` in some code paths, meaning `timeout_seconds` is
passed through in good faith but is not unconditionally guaranteed to be
enforced by the SDK in every situation. This is a vendor-SDK limitation,
not something `GeminiProvider` can fix from the kernel side; documented
here and in `docs/specs/providers.md` rather than silently assumed to
work.

### Request translation / role-message mapping

`invoke()`'s request shape reuses **`OpenAIProvider`'s key names**
(`messages`, each `{"role": str, "content": str}`, `max_tokens`) rather
than inventing Gemini-specific ones -- a deliberate choice: Gemini is,
like OpenAI, a genuinely multi-turn message-list API (unlike Claude's
flat-prompt-plus-separate-system-field shape), so reusing the established
key names minimizes integration surprise for a consumer already handling
`OpenAIProvider`'s shape. This sprint's proof point is vendor-neutrality
of the *provider contract*, not inventing a third distinct request
schema for its own sake.

**Role mapping**, the one genuine translation decision this sprint makes:

| Kernel `role` | Gemini destination |
|---|---|
| `"system"` | `GenerateContentConfig.system_instruction` -- **not** a message in `contents`, since the Gemini API does not accept a `"system"` role inside `contents` at all (unlike OpenAI, which expresses a system prompt as an ordinary message). At most one `"system"`-role entry is accepted; a second raises `GeminiProviderError` rather than silently concatenating or picking one -- deterministic, fail-loud, matching this codebase's existing validation style. |
| `"user"` | Gemini `Content(role="user", ...)` -- passthrough. |
| `"assistant"` | Gemini `Content(role="model", ...)` -- **translated**, since Gemini's own vocabulary for a model turn is `"model"`, not `"assistant"`. This is the one true role-name mapping this sprint performs. |
| anything else | Rejected with `GeminiProviderError` naming the invalid role, the same strict-validation style `OpenAIProvider._validate_messages` already uses. |

At least one non-system message is required (`GeminiProviderError` if
`messages` is empty, missing, not a list, or reduces to only
system-role entries after mapping). No alternating-turn-order validation
is performed by the kernel -- the Gemini API itself is trusted to reject
a malformed conversational structure, exactly as neither
`ClaudeProvider` nor `OpenAIProvider` validates turn ordering today.

`max_tokens` (default `1024`, for consistency with both existing
providers' request-shape convention, though the Gemini API itself does
not require it) maps to `GenerateContentConfig.max_output_tokens`.

### System instruction behavior

Exactly one optional `system_instruction` string, passed through
`GenerateContentConfig`, matching Gemini's own model (a config-level
field, not a `contents` entry) -- structurally the same shape
`ClaudeProvider`'s separate `system` request field already uses, applied
here via message-role extraction rather than a dedicated top-level
request key, since this sprint deliberately reuses `OpenAIProvider`'s
message-list request shape (see above).

### Tool/function-call mapping

**Not supported, intentionally.** `ProviderCapabilities.supports_tool_calls`
remains `False` (the class default) for `GeminiProvider`, matching both
existing providers exactly -- per the architecture review's point 2
above, this is honest, ratified-accurate metadata, not an aspiration.
`google-genai` supports function calling (`types.Part.from_function_call`,
tool declarations on `GenerateContentConfig`); none of it is wired into
this provider. This is the "document as intentionally unsupported rather
than expanding the kernel surface" instruction applied directly.

### Token/usage metadata mapping

`response.usage_metadata.prompt_token_count` -> `prompt_tokens`,
`.candidates_token_count` -> `completion_tokens` -- both defensively
defaulted to `0` if `usage_metadata` is absent or either field is
unset (`None`), the same defensive pattern `OpenAIProvider.invoke` already
uses for `completion.usage`. `usage_metadata` carries several other
fields (`cached_content_token_count`, `thoughts_token_count`,
`tool_use_prompt_token_count`, ...) not surfaced in this sprint's
response shape -- consistent with reusing `OpenAIProvider`'s two-field
usage shape rather than inventing a wider one; see "intentionally
unsupported" below.

### Response normalization

```python
response = {
    "text": str,
    "model": str,
    "finish_reason": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

`text` comes from `GenerateContentResponse.text` -- the SDK's own
quick-accessor, confirmed by direct source inspection to safely return
`None` (never raise) when there are no candidates or no text parts,
rather than a hand-rolled equivalent. `model` is `self._model` (the
configured/requested model identifier), a deliberate simplification: the
response object's own `model_version` field exists but its
reliability/presence was not independently verified with the same rigor
as the fields above, and `self._model` is always correct for "the model
this request targeted" -- unlike `ClaudeProvider`/`OpenAIProvider`, which
echo the response's own `model` field, this is a documented,
intentional difference, not an oversight. `finish_reason` is
`candidate.finish_reason.value` (a plain `str`, e.g. `"STOP"` --
confirmed `FinishReason` is a string-valued enum whose default `str()`
includes the enum's qualified name, so `.value` is used explicitly for a
clean, JSON-serializable string) if a candidate exists and has a
`finish_reason`, else `None`.

### Safety/filter response handling

Verified directly: `GenerateContentResponse.text` already returns `None`
safely for both an entirely-blocked prompt (`candidates` empty) and a
candidate with no usable text parts. `invoke()` treats "no text" as one
category, `GeminiResponseError`, distinguishing *why* in the message
without inventing a new exception type for it -- consistent with
`ClaudeResponseError`/`OpenAIResponseError`'s existing scope ("the
response contained no text content," which a safety-filtered response
genuinely is a case of):

- If `response.candidates` is empty, the message names
  `response.prompt_feedback.block_reason` (e.g. `"SAFETY"`,
  `"PROHIBITED_CONTENT"`) when present -- the prompt itself was blocked
  before any candidate was generated.
- Otherwise, the message names the first candidate's `finish_reason`
  (e.g. `"SAFETY"`, `"MAX_TOKENS"` with an empty response, `"RECITATION"`)
  -- generation started but produced no usable text.

Neither path raises a dedicated `GeminiSafetyError` or similar --
deliberately, to keep the five-class shape the Sprint 25 audit ratified
as the stable contract (`GeminiProviderError`/`GeminiAuthenticationError`/
`GeminiTimeoutError`/`GeminiConnectionError`/`GeminiResponseError`) rather
than growing a sixth, Gemini-specific category no other provider has an
equivalent for.

### Provider error translation

`google.genai.errors.APIError` (base for `ClientError`/`ServerError`,
confirmed by direct source inspection) exposes `.code` (the HTTP status
integer) and a message assembled from the response body -- structurally
different from `anthropic`/`openai`, which expose dedicated
`AuthenticationError`/`RateLimitError`/`APITimeoutError`/
`APIConnectionError` subclasses. `google-genai` does not distinguish
those by exception type, only by `.code`:

| Failure | Detection | Kernel exception |
|---|---|---|
| Authentication rejected | `errors.APIError` with `.code in (401, 403)` | `GeminiAuthenticationError` |
| Any other API-level failure (`4xx`/`5xx`, including `429` rate-limiting, which `google-genai` also routes through the generic `ClientError`/`.code` path with no dedicated subclass) | `errors.APIError`, `.code` not `401`/`403` | `GeminiProviderError` (the base, generic bucket) -- exactly where `ClaudeProvider`/`OpenAIProvider` already bucket a rate-limit failure today, since neither catches its SDK's own dedicated `RateLimitError` subclass separately either; see `docs/specs/providers.md`'s existing error-model sections. |
| Request timed out | `httpx.TimeoutException` -- confirmed by source/issue-tracker research that `google-genai`'s transport-level failures are **not** wrapped by `errors.APIError` (which only handles a completed HTTP response with an error status); a genuine timeout never receives a response to wrap, so the underlying `httpx` exception propagates from the SDK uncaught | `GeminiTimeoutError` |
| Network/connection failure | `httpx.TransportError` (the broader base `TimeoutException` also derives from -- caught second, after the more specific `TimeoutException`, the same ordering `ClaudeProvider`/`OpenAIProvider` already use for their own SDK-specific timeout/connection pairs) | `GeminiConnectionError` |

No `google.genai`/`httpx` exception ever crosses `GeminiProvider`'s
boundary uncaught -- verified by a dedicated test mirroring
`test_sdk_exceptions_never_escape_the_provider` in both existing provider
test files.

### Streaming behavior

**Not implemented**, matching `ClaudeProvider`/`OpenAIProvider` exactly.
Permitted without breaking any contract expectation, since
`ProviderCapabilities.supports_streaming` is descriptive metadata only
(architecture review point 2) and `BaseProvider` has no dedicated
streaming abstract method to satisfy. `google-genai` exposes
`generate_content_stream()` separately; this provider does not call it.

### Cancellation behavior

Not applicable. `invoke()` and `check_health()` are single synchronous
calls with no long-lived operation, streaming session, or async task to
cancel -- the same "not relevant" status `ClaudeProvider`/`OpenAIProvider`
already have.

### Deterministic testing strategy

`tests/providers/test_gemini.py` mirrors `test_claude.py`/`test_openai.py`'s
established pattern exactly: `pytest.importorskip("google.genai")` and
`pytest.importorskip("httpx")` at import time (so the rest of the suite
stays green without the optional dependency installed), a fake object
providing `.models.generate_content(**kwargs) -> types.GenerateContentResponse`
injected via `GeminiProvider`'s `client` constructor parameter, and real
`google.genai.types`/`google.genai.errors` objects constructed directly
(no live network I/O, ever) -- the same fidelity `_make_message`/
`_make_completion` already achieve for the other two providers.

### Dependency impact

`providers` continues to depend only on `core`. `providers/gemini.py`
additionally depends on the new optional `google-genai` package (which
itself depends on `httpx`, already present transitively via `anthropic`/
`openai`) -- the third, and only the third, file in this repository that
imports `google.genai`; it does not depend on, and is not depended on by,
`claude.py` or `openai.py`.

### Compatibility guarantees

No change to `BaseProvider`, `ProviderCapabilities`, `ProviderConfiguration`,
`ProviderHealthCheck`, `ProviderRegistry`, `ProviderFactory`,
`ProviderError`, `ProviderConfigurationError`, or
`ProviderRegistrationError` -- verified by the full pre-existing test
suite (769 tests as of Sprint 28) passing unmodified. `GeminiProvider`
and its five-class exception hierarchy
(`GeminiProviderError`/`GeminiAuthenticationError`/`GeminiTimeoutError`/
`GeminiConnectionError`/`GeminiResponseError`) are new, additive, and not
exported from `mellivor_kernel.providers.__all__` -- a MINOR-compatible
addition per [ADR-0005](0005-versioning-strategy.md), the same shape
Sprint 23's `OpenAIProvider` addition already was.

### Intentionally unsupported Gemini-specific features

Documented here, not silently omitted, per this sprint's explicit
instruction:

- **Streaming** (`generate_content_stream`) -- see above.
- **Tool/function calling** (`types.Part.from_function_call`, tool
  declarations) -- see "Tool/function-call mapping" above.
- **Multimodal input** (image/video/audio/PDF via `Part.from_bytes`/
  `Part.from_uri`) -- text-only, matching both existing providers'
  text-only scope.
- **Vertex AI authentication** (`vertexai=True`, GCP `project`/
  `location`) -- Gemini Developer API (`api_key`) only; see "Credential
  handling" above.
- **Grounding/search tools, code execution, context caching, batch
  generation, the Live/bidirectional API, embeddings** -- none wired in;
  `google-genai` supports all of these, none is reachable through this
  provider.
- **`response.usage_metadata`'s cache/thoughts/tool-use token fields** --
  only `prompt_token_count`/`candidates_token_count` are surfaced, the
  same two-field shape `OpenAIProvider` already established.
- **Multiple candidates** (`candidate_count > 1`) -- not requested;
  `GeminiProvider` always reads `response.candidates[0]` only,
  matching `GenerateContentResponse.text`'s own single-candidate
  convenience-accessor behavior.

## Alternatives considered

- **The deprecated `google-generativeai` package.** Rejected -- see
  "Client/library choice" above. Fully unsupported by Google as of this
  sprint's date.
- **Direct HTTP against the Gemini REST API**, bypassing any SDK.
  Rejected -- see "Client/library choice" above: reimplements what
  `google-genai` already does correctly and Google maintains, for no
  isolation benefit this module doesn't already have as the sole
  `google.genai` importer.
- **Vertex AI as the auth/backend path** (`google-cloud-aiplatform` or
  `google-genai`'s own `vertexai=True` mode). Rejected for this sprint:
  explicitly excluded by this sprint's own scope ("no cloud-specific
  control planes"), and would require GCP project/location/credentials
  configuration fields `ProviderConfiguration` does not have -- a real,
  larger design question deferred, not silently worked around.
- **Inventing a Gemini-specific request/response key-naming scheme**
  (for example `"contents"`/`"parts"` mirroring the SDK's own
  vocabulary) instead of reusing `OpenAIProvider`'s `"messages"`/
  `"content"` names. Rejected: this sprint's proof point is that the
  *provider contract* (`BaseProvider`) is vendor-neutral, which reusing
  a message-list shape across two structurally-similar providers
  demonstrates at least as well as inventing a third vocabulary, with
  less integration surprise for any caller already handling
  `OpenAIProvider`.
- **A dedicated `GeminiSafetyError`/`GeminiBlockedError` exception
  class** for safety-filtered responses. Rejected: would grow the
  ratified five-class shape to six for one provider, and
  `GeminiResponseError`'s existing scope ("no usable text content")
  already covers it correctly without a new category; the *reason* is
  preserved in the exception's message instead.
- **Echoing `response.model_version` as the response's `"model"` field**,
  matching `ClaudeProvider`/`OpenAIProvider`'s pattern of echoing the
  response's own model field. Considered and set aside for this sprint:
  `self._model` (the requested model) is simpler, always correct, and
  was preferred over asserting a specific reliability guarantee about
  `model_version` that wasn't independently verified to the same
  standard as every other field this ADR relies on -- documented as a
  deliberate, not accidental, difference.

## Consequences

- `mellivor_kernel.providers.gemini` is a new, optional-dependency
  module; `mellivor_kernel.providers.__all__` is unchanged (seven names,
  as before).
- A consuming product (Mellivor One, Mellivor AI Security) now has a
  third provider option, composable through the existing
  `ProviderFactory`/`ProviderRegistry`/`AIEngineBuilder` machinery with
  no special-casing -- proven directly by
  `tests/test_gemini_provider_integration.py`, mirroring
  `test_openai_provider_integration.py`'s full `AIEngineBuilder ->
  AIEngine.execute() -> ExecutionEngine -> Dispatcher -> GeminiProvider
  -> ExecutionResult` path.
- `pyproject.toml` gains one new optional-dependency group (`gemini`);
  CI (`.github/workflows/ci.yml`) installs it alongside `anthropic`/
  `openai` so the full suite runs against a real (fake-client-only, no
  network) `GeminiProvider` on every push.
- This ADR neither promises nor precludes a fourth provider (a local
  model, per ADR-0019's own "Deferred to v1.1" wording) later; any such
  addition is its own scoped decision, following this ADR's and Sprint
  10's precedent, not implied by this one.
- The documented `google-genai` timeout-override limitation (see
  "Credential handling") is a vendor-SDK issue tracked upstream, not a
  defect in this provider -- recorded here so a future maintainer does
  not rediscover it from scratch.
