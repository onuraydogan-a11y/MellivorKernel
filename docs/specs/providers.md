# `providers` subsystem spec

Status: Implemented (Sprint 3) — interfaces and registry only, no concrete
providers.

Public contract exported from `mellivor_kernel.providers`. Anything not
listed here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## Scope of this sprint

This spec covers the provider *abstraction* only: the contract every AI
model provider must implement, and the registry/factory infrastructure for
managing provider instances. No concrete provider (OpenAI, Anthropic,
Gemini, a local model, or otherwise) is implemented here or anywhere else
in this repository — per
[ADR-0003](../adr/0003-repository-boundaries.md), provider-specific SDK
integrations belong in `providers/`, but are a separate, future addition,
not part of this spec.

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

## Dependency relationship

`providers` depends only on `core` (for `KernelError`), matching the
`config → core` precedent from Sprint 2. `core` has no dependency on
`providers`. `providers` has no dependency on `config` or any other
subsystem.
