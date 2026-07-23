# `providers` subsystem spec

Status: Implemented (Sprint 3: interfaces and registry; Sprint 10: first
concrete provider, `ClaudeProvider`).

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
request  = {"prompt": str, "system": str | None, "max_tokens": int | None}
response = {
    "text": str, "model": str, "stop_reason": str | None,
    "input_tokens": int, "output_tokens": int,
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
registry.register(factory.create(ProviderConfiguration(
    provider_name="claude", api_key=api_key, default_model="claude-sonnet-5",
)))
```

or directly: `registry.register(ClaudeProvider(configuration))`. See
`tests/test_claude_provider_integration.py` for both paths exercised, plus
the full `ExecutionRequest -> ExecutionEngine -> Authorization ->
Dispatcher -> ClaudeProvider -> ExecutionResult` flow with `execution` and
`authorization` completely unmodified.

## Dependency relationship

`providers` depends only on `core` (for `KernelError`), matching the
`config → core` precedent from Sprint 2. `core` has no dependency on
`providers`. `providers` has no dependency on `config` or any other
subsystem. `providers/claude.py` additionally depends on the optional
`anthropic` package — the only file in this repository that does.
