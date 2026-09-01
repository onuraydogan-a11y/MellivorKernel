# `providers` subsystem spec

Status: Implemented (Sprint 3: interfaces and registry; Sprint 10: first
concrete provider, `ClaudeProvider`; Sprint 23: second, `OpenAIProvider`;
Sprint 29: third, `GeminiProvider`).

Public contract exported from `mellivor_kernel.providers`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## Scope of this sprint (Sprint 3)

This spec originally covered the provider *abstraction* only: the contract
every AI model provider must implement, and the registry/factory
infrastructure for managing provider instances, with no concrete provider
implemented anywhere in this repository. Per
[ADR-0003](../adr/0003-repository-boundaries.md), integrations with
*infrastructure* providers — model providers among them — belong under
`providers/`; it is business-application integrations (CRM, HRIS, and the
like) that belong outside this repository. Sprint 10 exercises that rule
for the first time — see [`ClaudeProvider`](#claudeprovider-sprint-10)
below.

## Exceptions

`providers/exceptions.py` — subclasses `core.exceptions.KernelError`
(re-exported, not redefined, from `core`), not the reverse: `core` has no
dependency on `providers`.

- `ProviderError` — base class for every exception this subsystem raises.
- `ProviderConfigurationError` — invalid, missing, or malformed provider
  configuration.
- `ProviderRegistrationError` — a registration or lookup failure, in
  either `ProviderRegistry` or `ProviderFactory`.

## `ProviderCapabilities`

An immutable (`frozen=True, slots=True`) dataclass describing what a
provider supports: `supports_streaming`, `supports_tool_calls`,
`supports_vision`, `supports_embeddings` (all `bool`, default `False`), and
`max_context_tokens: int | None` (default `None`).

These flags are descriptive metadata only in this sprint. They do not
correspond to dedicated abstract methods on `BaseProvider` (for example, a
dedicated streaming API) — declaring `supports_streaming=True` does not
obligate a provider to implement anything beyond `invoke`. That refinement
is deliberately deferred until a real provider's actual streaming/tool-call
API shape is known.

## `ProviderConfiguration`

An immutable (`frozen=True, slots=True`) dataclass:

```python
provider_name: str
default_model: str | None = None
api_key: str | None = None
base_url: str | None = None
timeout_seconds: float = 30.0
max_retries: int = 0
extra: Mapping[str, object] = field(default_factory=dict)
```

`__post_init__` raises `ProviderConfigurationError` if `provider_name` is
empty/whitespace, `timeout_seconds` is not positive, or `max_retries` is
negative. `api_key` is stored as given and not validated for format or
authenticity.

## `ProviderHealthCheck`

An immutable (`frozen=True, slots=True`) dataclass:
`{healthy: bool, provider_name: str, detail: str = ""}` — a point-in-time
report, mirroring `core.runtime.HealthStatus`'s shape. Producing one is a
concrete provider's responsibility (via `BaseProvider.check_health()`);
nothing in this sprint performs an actual reachability check, since there
is no concrete provider to check.

## `BaseProvider` (contract)

An `ABC`, not a `Protocol` — concrete providers are expected to literally
subclass it, unlike `core.contracts.KernelSettings` (a structural contract
used for dependency inversion, not subclassing).

- `__init__(self, configuration: ProviderConfiguration)` — concrete,
  inherited by all subclasses; stores `configuration`.
- `.configuration` — read-only property exposing the constructor argument.
- `.name -> str` (abstract) — a short, unique identifier, e.g. `"openai"`.
- `.capabilities -> ProviderCapabilities` (abstract).
- `.check_health() -> ProviderHealthCheck` (abstract).
- `.invoke(request: Mapping[str, object]) -> Mapping[str, object]`
  (abstract) — invokes the underlying model.

**Deliberate scope limitation:** `invoke`'s request/response is a generic
`Mapping[str, object]`, not a concrete message/chat/tool-calling schema.
Designing that schema is a real design decision in its own right (message
format, streaming, tool-calling, multimodal input) and is out of scope for
"interfaces and registry only" — it is left for a future sprint once a real
provider's requirements can inform it, rather than being guessed here.

`BaseProvider` cannot be instantiated directly, nor can a subclass that
leaves any abstract member unimplemented (standard `ABC` enforcement,
raises `TypeError` at construction time).

## `ProviderRegistry`

Holds already-constructed `BaseProvider` instances, keyed by each
provider's own `.name`.

- `register(provider)` — raises `ProviderRegistrationError` if that name
  is already registered.
- `get(name) -> BaseProvider` — raises `ProviderRegistrationError` if
  unregistered.
- `is_registered(name) -> bool`.
- `list_providers() -> tuple[str, ...]`.

No un-registration, scoping, or capability-based lookup — kept to what
this sprint's registration/lookup requirement asked for.

## `ProviderFactory`

Builds `BaseProvider` instances from a `ProviderConfiguration`. Has no
import-time or runtime knowledge of any concrete provider — provider
*implementations* register their own constructor here under a provider
type name.

- `register_provider_type(provider_name, constructor)` — `constructor` is
  `Callable[[ProviderConfiguration], BaseProvider]`. Raises
  `ProviderRegistrationError` if `provider_name` already has one.
- `create(configuration) -> BaseProvider` — looks up the constructor for
  `configuration.provider_name` and calls it. Raises
  `ProviderRegistrationError` if none is registered.
- `is_registered(provider_name) -> bool`.

`ProviderFactory` (constructs instances) and `ProviderRegistry` (holds
already-built instances) are intentionally decoupled — neither depends on
the other. A caller composes them explicitly:
`registry.register(factory.create(config))`, as exercised in
`tests/test_provider_bootstrap.py`.

## `ClaudeProvider` (Sprint 10)

`mellivor_kernel.providers.claude.ClaudeProvider` — a `BaseProvider`
implementation backed by the Anthropic Messages API, and the kernel's
reference implementation for concrete providers. **Not exported from
`mellivor_kernel.providers.__all__`** — imported explicitly from
`mellivor_kernel.providers.claude`, the same separation
`tools.builtin`'s demonstration tools keep from `tools`'s own contract.
This keeps the base `providers` package free of any vendor SDK dependency
for consumers who never use Claude.

**Optional dependency.** Requires the `anthropic` package:
`pip install mellivor-kernel[anthropic]`. `providers/claude.py` is the
only module anywhere in this repository that imports `anthropic` — no
other kernel code imports this module or the SDK.

**Scope, deliberately minimal:** synchronous request/response, plain text
prompts, plain text responses. No streaming, tool calling, vision, images,
PDFs, JSON mode, function calling, prompt caching, MCP, or batch
execution — all left for a future sprint, once (if) a real need for them
is established.

### Configuration

Read only from the existing `ProviderConfiguration` — no provider-specific
global configuration is introduced:

| Field | Required | Meaning |
|---|---|---|
| `api_key` | **Yes** | The Anthropic API key. **Does not fall back to the `ANTHROPIC_API_KEY` environment variable** — the Anthropic SDK does that by default, which would be exactly the provider-specific global configuration this sprint's scope excludes; `ClaudeProvider` raises `ProviderConfigurationError` at construction if unset, rather than silently reading the environment. |
| `default_model` | **Yes** | The model used for every request (e.g. `"claude-sonnet-5"`). Raises `ProviderConfigurationError` at construction if unset. |
| `timeout_seconds` | No | Passed through to the Anthropic client's own `timeout`. Defaults to `ProviderConfiguration`'s own default (`30.0`). |
| `base_url` | No | Passed through as given; `None` leaves the Anthropic client's own default/environment-driven resolution in place (a routing default, not a credential, so left unguarded unlike `api_key`). |
| `max_retries` | No | Passed through to the Anthropic client's own retry mechanism. |

**Convention for future providers:** any credential field (an API key, a
token) should be required explicitly from `ProviderConfiguration` and
never fall back to an SDK's own environment-variable lookup, for the same
reason `api_key` is required here. Non-credential fields (`base_url` and
similar) are lower-stakes and may reasonably defer to an SDK's own
default/environment resolution.

### Request / response shape

`invoke()`'s request and response are each a plain `Mapping[str, object]`,
as `BaseProvider.invoke` has always allowed — `ClaudeProvider` defines its
own minimal shape rather than a shared cross-provider schema (still an
open design question per `BaseProvider`'s "deliberate scope limitation"
above):

```python
request = {"prompt": str, "system": str | None, "max_tokens": int | None}
response = {
    "text": str,
    "model": str,
    "stop_reason": str | None,
    "input_tokens": int,
    "output_tokens": int,
}
```

`prompt` is required (non-empty string); `system` and `max_tokens`
(default `1024`, Anthropic requires a value on every request) are
optional.

### Error model

`providers/claude.py`'s own exception hierarchy, all subclassing
`ProviderError` — no `anthropic` SDK exception ever escapes `ClaudeProvider`:

- `ClaudeProviderError` — base class; also raised for malformed requests
  and any Anthropic API failure not covered by a more specific type below.
- `ClaudeAuthenticationError` — the API rejected the configured
  credentials (`anthropic.AuthenticationError`).
- `ClaudeTimeoutError` — the request timed out (`anthropic.APITimeoutError`).
- `ClaudeConnectionError` — a network failure prevented the request from
  completing (`anthropic.APIConnectionError`).
- `ClaudeResponseError` — the response contained no text content.

### `check_health()`

Issues a minimal real request (`max_tokens=1`) through the same client and
error handling `invoke()` uses, reporting `healthy=False` with the
failure's detail on any `anthropic.AnthropicError` rather than raising —
a live reachability check, not just a configuration-presence check
(construction already guarantees `api_key`/`default_model` are set).

### Registration

No bootstrap wiring is added — `ClaudeProvider` is registered the same way
any provider is, via the existing `ProviderFactory`/`ProviderRegistry`
composition:

```python
factory = ProviderFactory()
factory.register_provider_type("claude", ClaudeProvider)
registry = ProviderRegistry()
registry.register(
    factory.create(
        ProviderConfiguration(
            provider_name="claude",
            api_key=api_key,
            default_model="claude-sonnet-5",
        )
    )
)
```

or directly: `registry.register(ClaudeProvider(configuration))`. See
`tests/test_claude_provider_integration.py` for both paths exercised, plus
the full `ExecutionRequest -> ExecutionEngine -> Authorization ->
Dispatcher -> ClaudeProvider -> ExecutionResult` flow with `execution` and
`authorization` completely unmodified.

## `OpenAIProvider` (Sprint 23)

`mellivor_kernel.providers.openai.OpenAIProvider` — a `BaseProvider`
implementation backed by the OpenAI Chat Completions API, and the
kernel's second concrete provider. Proves `BaseProvider`'s existing
contract generalizes to a genuinely different request shape than
`ClaudeProvider`'s, not a second copy of it — deliberately chosen for
that reason (see [ADR-0018](../adr/0018-ai-engine-foundation.md)'s own
"smallest useful slice" reasoning, applied here to provider selection).
**Not exported from `mellivor_kernel.providers.__all__`** — imported
explicitly from `mellivor_kernel.providers.openai`, the same separation
`ClaudeProvider` keeps from the base `providers` package.

**Optional dependency.** Requires the `openai` package:
`pip install mellivor-kernel[openai]`. `providers/openai.py` is the only
module anywhere in this repository that imports `openai` — no other
kernel code imports this module or the SDK, mirroring `claude.py`'s
isolation of `anthropic` exactly.

**Scope, deliberately minimal:** synchronous request/response, plain
message-list prompts, plain text responses. No streaming, tool calling,
vision, JSON mode, function calling, prompt caching, or batch
execution — the same exclusions `ClaudeProvider` already established,
applied identically here.

### Configuration

Read only from the existing `ProviderConfiguration` — no provider-specific
global configuration is introduced, following the convention
`ClaudeProvider`'s own spec section already states for future providers:

| Field | Required | Meaning |
|---|---|---|
| `api_key` | **Yes** | The OpenAI API key. **Does not fall back to the `OPENAI_API_KEY` environment variable** — the OpenAI SDK does that by default; `OpenAIProvider` raises `ProviderConfigurationError` at construction if unset, for the same reason `ClaudeProvider` does. |
| `default_model` | **Yes** | The model used for every request (e.g. `"gpt-4o"`). Raises `ProviderConfigurationError` at construction if unset. |
| `timeout_seconds` | No | Passed through to the OpenAI client's own `timeout`. Defaults to `ProviderConfiguration`'s own default (`30.0`). |
| `base_url` | No | Passed through as given; `None` leaves the OpenAI client's own default/environment-driven resolution in place, the same non-credential exception `ClaudeProvider` already documents for this field. |
| `max_retries` | No | Passed through to the OpenAI client's own retry mechanism. |

### Request / response shape

`invoke()`'s request and response are each a plain `Mapping[str, object]`,
defined on their own terms rather than reused from `ClaudeProvider` — a
deliberate structural difference proving `BaseProvider`'s generic
contract accommodates more than one shape:

```python
request = {"messages": list[{"role": str, "content": str}], "max_tokens": int | None}
response = {
    "text": str,
    "model": str,
    "finish_reason": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

`messages` is required (a non-empty list, each entry a mapping with
string `role` and string `content` — including a system prompt, which
OpenAI expresses as an ordinary message with `role: "system"` rather
than `ClaudeProvider`'s separate `system` field; this is the one
concrete API-shape difference this sprint is designed to surface, not
paper over). `max_tokens` (default `1024`, for consistency with
`ClaudeProvider`'s own request-shape convention, though the OpenAI API
itself does not require it) is optional.

### Error model

`providers/openai.py`'s own exception hierarchy, all subclassing
`ProviderError` — no `openai` SDK exception ever escapes
`OpenAIProvider`:

- `OpenAIProviderError` — base class; also raised for malformed requests
  and any OpenAI API failure not covered by a more specific type below.
- `OpenAIAuthenticationError` — the API rejected the configured
  credentials (`openai.AuthenticationError`).
- `OpenAITimeoutError` — the request timed out (`openai.APITimeoutError`,
  which the SDK defines as a subclass of `APIConnectionError` — caught
  ahead of it, the same ordering `ClaudeProvider` already uses for the
  equivalent `anthropic` pair).
- `OpenAIConnectionError` — a network failure prevented the request from
  completing (`openai.APIConnectionError`).
- `OpenAIResponseError` — the response contained no text content (for
  example, a tool-call-only response, which this sprint's plain-text
  scope does not interpret).

### `check_health()`

Issues a minimal real request (`max_tokens=1`) through the same client
and error handling `invoke()` uses, reporting `healthy=False` with the
failure's detail on any `openai.OpenAIError` rather than raising — a
live reachability check, the same shape `ClaudeProvider.check_health()`
already uses.

### Registration

No bootstrap wiring is added — `OpenAIProvider` is registered the same
way any provider is, via the existing `ProviderFactory`/`ProviderRegistry`
composition, or directly: `registry.register(OpenAIProvider(configuration))`.
See `tests/test_openai_provider_integration.py` for the full
`AIEngineBuilder -> AIEngine.execute() -> ExecutionEngine -> Dispatcher ->
OpenAIProvider -> ExecutionResult` flow — routed through the AI Engine
Foundation ([ADR-0018](../adr/0018-ai-engine-foundation.md)) rather than
a hand-built `Dispatcher`/`ExecutionEngine`, unlike `ClaudeProvider`'s own
Sprint 10 integration test, which predates `ai_engine`'s existence.

## `GeminiProvider` (Sprint 29)

`mellivor_kernel.providers.gemini.GeminiProvider` — a `BaseProvider`
implementation backed by the Gemini Developer API, and the kernel's
third concrete provider. Proves `BaseProvider`'s existing contract
generalizes to a genuinely different vendor SDK integration shape than
either existing provider's (a `.code`-based error model instead of
dedicated exception subclasses, and transport-level failures the SDK
does not itself wrap) — see
[ADR-0023](../adr/0023-gemini-provider.md) for the full design,
including why `google-genai` (not the deprecated
`google-generativeai` package) was selected. **Not exported from
`mellivor_kernel.providers.__all__`** — imported explicitly from
`mellivor_kernel.providers.gemini`, the same separation `ClaudeProvider`/
`OpenAIProvider` already keep from the base `providers` package.

**Optional dependency.** Requires the `google-genai` package:
`pip install mellivor-kernel[gemini]` (`google-genai>=2.0`).
`providers/gemini.py` is the only module anywhere in this repository
that imports `google.genai` — no other kernel code imports this module
or the SDK, mirroring `claude.py`'s/`openai.py`'s isolation exactly.

**Scope, deliberately minimal:** synchronous request/response, plain
message-list prompts (reusing `OpenAIProvider`'s request/response key
names, not inventing a third vocabulary), plain text responses. No
streaming, tool calling, vision, multimodal input, Vertex AI
authentication, context caching, or batch execution — the same
exclusions `ClaudeProvider`/`OpenAIProvider` already established, applied
identically here; see ADR-0023's "Intentionally unsupported Gemini-
specific features" for the complete, explicit list.

### Configuration

Read only from the existing `ProviderConfiguration` — no provider-specific
global configuration is introduced, following the same convention
`ClaudeProvider`'s spec section states for future providers:

| Field | Required | Meaning |
|---|---|---|
| `api_key` | **Yes** | The Gemini Developer API key. **Does not fall back to the `GOOGLE_API_KEY`/`GEMINI_API_KEY` environment variables** — the SDK does that by default; `GeminiProvider` raises `ProviderConfigurationError` at construction if unset, for the same reason `ClaudeProvider`/`OpenAIProvider` do. |
| `default_model` | **Yes** | The model used for every request (e.g. `"gemini-2.0-flash-001"`). Raises `ProviderConfigurationError` at construction if unset. |
| `timeout_seconds` | No | Passed through, converted to milliseconds, via `genai.Client(http_options=types.HttpOptions(timeout=...))` — a real, verified structural difference from `anthropic`/`openai`, which take `timeout` directly on the client. **Known vendor-SDK limitation:** `google-genai` has a documented issue where this can be overridden internally in some code paths; not something this provider can fix. |
| `base_url` | No | Also passed through via `http_options`, not a direct client kwarg (see above). `None` leaves the SDK's own default endpoint in place. |
| `max_retries` | No | Passed through via `http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=...))`. |

Gemini Developer API authentication only (`api_key`) — Vertex AI's
project/location-based authentication is not supported; see ADR-0023.

### Request / response shape

```python
request = {"messages": list[{"role": str, "content": str}], "max_tokens": int | None}
response = {
    "text": str,
    "model": str,
    "finish_reason": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

Deliberately reuses `OpenAIProvider`'s key names (`messages`,
`finish_reason`, `prompt_tokens`, `completion_tokens`) rather than
inventing Gemini-specific ones — this sprint's proof point is
vendor-neutrality of the provider *contract*, not a fourth distinct
schema. `messages` is required (a non-empty list, each entry a mapping
with string `role`/`content`). Role mapping:

| Kernel `role` | Gemini destination |
|---|---|
| `"system"` | `GenerateContentConfig.system_instruction` — **not** a `contents` entry (unlike OpenAI, Gemini does not accept a `"system"` role inside its message list). At most one; a second raises `GeminiProviderError`. |
| `"user"` | Gemini `Content(role="user", ...)` — passthrough. |
| `"assistant"` | Gemini `Content(role="model", ...)` — **translated**, since Gemini's own vocabulary for a model turn is `"model"`. |
| anything else | Rejected with `GeminiProviderError`. |

`response["model"]` is the configured/requested model
(`self._model`), not echoed from the response object — a deliberate
difference from `ClaudeProvider`/`OpenAIProvider`, which echo the
response's own `model` field; see ADR-0023's "Response normalization."
A response (or the prompt itself) with no usable text — including a
safety-filtered block — raises `GeminiResponseError` naming
`prompt_feedback.block_reason` or the candidate's `finish_reason`; see
ADR-0023's "Safety/filter response handling." `max_tokens` (default
`1024`) maps to `GenerateContentConfig.max_output_tokens`.

### Error model

`providers/gemini.py`'s own exception hierarchy, all subclassing
`ProviderError` — no `google.genai`/`httpx` exception ever escapes
`GeminiProvider`:

- `GeminiProviderError` — base class; also raised for malformed requests
  and any Gemini API failure not covered by a more specific type below,
  **including a `429` rate-limit response** (`google-genai` has no
  dedicated rate-limit exception type, only a `.code`-based `ClientError`
  — the same generic bucket `ClaudeProvider`/`OpenAIProvider` already
  use for a rate limit today).
- `GeminiAuthenticationError` — the API rejected the configured
  credentials (`google.genai.errors.APIError` with `.code` `401` or
  `403` — `google-genai` has no dedicated authentication exception
  type, unlike `anthropic`/`openai`; detected by status code instead).
- `GeminiTimeoutError` — the request timed out (`httpx.TimeoutException`
  — `google-genai` does not wrap transport-level failures itself; the
  underlying `httpx` exception is caught directly).
- `GeminiConnectionError` — a network failure prevented the request from
  completing (`httpx.TransportError`, caught after the more specific
  `TimeoutException`).
- `GeminiResponseError` — the response contained no text content,
  including a safety-filtered block (see above).

### `check_health()`

Issues a minimal real request (`max_output_tokens=1`) through the same
client and error handling `invoke()` uses, reporting `healthy=False`
with the failure's detail on `errors.APIError`/`httpx.TimeoutException`/
`httpx.TransportError` rather than raising — the same live reachability
check shape `ClaudeProvider.check_health()`/`OpenAIProvider.check_health()`
already use.

### Registration

No bootstrap wiring is added — `GeminiProvider` is registered the same
way any provider is, via the existing `ProviderFactory`/`ProviderRegistry`
composition, or directly: `registry.register(GeminiProvider(configuration))`.
See `tests/test_gemini_provider_integration.py` for the full
`AIEngineBuilder -> AIEngine.execute() -> ExecutionEngine -> Dispatcher ->
GeminiProvider -> ExecutionResult` flow, mirroring `OpenAIProvider`'s own
Sprint 23 integration test.

## `LocalProvider` (Sprint 32)

`LocalProvider` is the first post-v1.1 provider. It connects to an explicitly
configured, already-running OpenAI-compatible Chat Completions endpoint. It
does not install or manage a runtime, download a model, launch a process,
probe during import/construction, or fall back to the internet or a cloud
provider. See [ADR-0026](../adr/0026-local-provider-openai-compatible-endpoint.md).

The provider is imported explicitly from `mellivor_kernel.providers.local`,
matching the optional-dependency isolation of Claude, OpenAI, and Gemini. It is
not added to `providers.__all__`, so the v1.1 base import surface remains
independent of HTTPX.

### Architecture and supported runtimes

The selected protocol is the OpenAI-compatible Chat Completions wire format,
not an Ollama-native or runtime-specific API. It supports conforming vLLM and
LM Studio servers and Ollama's compatibility endpoint without coupling the
kernel to any one runtime. A generic arbitrary-HTTP provider was rejected
because it has no stable interoperable schema.

### Configuration

| Field | Required | Meaning |
|---|---|---|
| `base_url` | **Yes** | Absolute `http`/`https` protocol root, normally ending in `/v1`. The provider appends `/chat/completions`. User information, query parameters, and fragments are rejected. No localhost default exists. |
| `default_model` | **Yes** | Non-blank model identifier sent with every request. |
| `api_key` | No | If present, sent as `Authorization: Bearer ...`. No environment or other credential fallback. |
| `timeout_seconds` | No | HTTPX request timeout; positive through `ProviderConfiguration`. |
| `max_retries` | No | Bounded retries for timeout/transport failures only; no retries for authentication, HTTP status, validation, or malformed responses. |

`pip install mellivor-kernel[local]` installs the optional
`httpx>=0.28.1,<1` transport. Base package dependencies remain empty.

### Request and response

```python
request = {
    "messages": list[{"role": "system" | "user" | "assistant", "content": str}],
    "max_tokens": int | None,
}
response = {
    "text": str,
    "model": str,
    "finish_reason": str | None,
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

Messages pass through in order with their OpenAI-compatible roles. Missing
usage counts normalize to zero. Unsupported request keys are rejected rather
than silently implying support for runtime-specific behavior.

### Error and health behavior

The additive hierarchy `LocalProviderError`, `LocalAuthenticationError`,
`LocalTimeoutError`, `LocalConnectionError`, and `LocalResponseError` mirrors
the provider error model ratified in Sprint 25. Authorization headers, API
keys, and response bodies never enter translated error messages.

`check_health()` explicitly performs a one-token chat completion and returns a
`ProviderHealthCheck`; it never raises a translated provider failure. No
health request occurs unless the caller invokes this method.

### Trust boundary and intentionally unsupported behavior

The configured endpoint is a caller-controlled network destination. Products
must treat it as privileged configuration and enforce their egress/SSRF policy
outside the adapter. The kernel validates URL shape but does not resolve DNS or
decide whether loopback, LAN, or remote private hosts are allowed.

Streaming, tools/functions, structured output, multimodal/vision input,
embeddings, model discovery/pulling, runtime installation/lifecycle, batching,
and endpoint failover are intentionally unsupported.

## v1.0 contract ratification (Sprint 25)

[ADR-0019](../adr/0019-release-readiness-and-scope-lock.md) classified
the provider abstraction `Included in v1.0` pending one closing
decision: whether each provider's four-way exception granularity has a
real consumer, and whether `ProviderCapabilities` should be exercised
with real flags or documented as aspirational. Both are now decided,
**as-is, with no code change**:

- **Exception granularity is ratified as the intentional, required
  shape of a provider's error model.** `ClaudeProviderError`/
  `ClaudeAuthenticationError`/`ClaudeTimeoutError`/`ClaudeConnectionError`/
  `ClaudeResponseError` and `OpenAIProvider`'s equivalent five-class
  hierarchy are the stable `1.0.0` contract, not a provisional pattern
  awaiting a consumer. Any future provider (see "Convention for future
  providers" above) is expected to define the same five-class shape
  (a base `<Vendor>ProviderError` plus `Authentication`/`Timeout`/
  `Connection`/`Response` subclasses translating that vendor's own SDK
  exceptions), whether or not anything in the kernel yet catches the
  specific subclasses — the granularity documents *what kind of failure
  occurred* for whatever catches `ProviderError` broadly today, and is
  available for a future consumer to narrow on without a contract
  change when one exists.
- **`ProviderCapabilities`'s current all-`False` values are accurate,
  not aspirational or unproven.** Both `ClaudeProvider` and
  `OpenAIProvider` genuinely support only synchronous, plain-text
  request/response in this sprint's scope — streaming, tool calls,
  vision, and embeddings are simply not implemented by either, so
  `ProviderCapabilities()`'s defaults describe them correctly. This
  matches the "descriptive metadata only" scope already stated above;
  no code change is needed for the metadata to be honest.

## Dependency relationship

`providers` depends only on `core` (for `KernelError`), matching the
`config → core` precedent from Sprint 2. `core` has no dependency on
`providers`. `providers` has no dependency on `config` or any other
subsystem. Concrete modules own only optional integrations:
`providers/claude.py` imports `anthropic`, `providers/openai.py` imports
`openai`, `providers/gemini.py` imports `google-genai`/`httpx`, and
`providers/local.py` imports `httpx`. None depends on another concrete
provider, and base package dependencies remain empty.
