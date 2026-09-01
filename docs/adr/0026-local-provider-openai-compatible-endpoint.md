# 0026. Local provider through an OpenAI-compatible endpoint

Status: Accepted
Date: 2026-09-01

## Context

Sprint 32 opens post-v1.1 development with the local-model provider deferred
by ADR-0019. The kernel must connect to a real, already-running inference
runtime without changing the frozen `BaseProvider`, installing or managing a
runtime, downloading a model, executing a command, or falling back to a cloud
service.

The existing provider contract already represents synchronous invocation,
health reporting, configuration, and normalized mapping results. The design
question is therefore which local serving protocol should sit behind a new
adapter, not whether the shared provider abstraction should grow.

## Decision

Add `providers.local.LocalProvider`, backed by the OpenAI-compatible Chat
Completions HTTP protocol. The caller must provide:

- `ProviderConfiguration.base_url`: an absolute `http` or `https` URL for an
  already-running trusted endpoint; no localhost default;
- `ProviderConfiguration.default_model`: the model identifier sent with each
  request; and
- the existing positive `timeout_seconds` and non-negative `max_retries`.

`api_key` is optional. When present it is sent only as a Bearer authorization
header. No environment lookup or other credential fallback occurs.

The adapter appends `/chat/completions` to the configured base URL. A caller
therefore normally configures the protocol root, for example
`http://inference.internal:8000/v1`. URLs with user information, query
parameters, or fragments are rejected so credentials and ambiguous routing do
not hide inside endpoint strings.

The provider uses optional `httpx>=0.28.1,<1`, owned by a new `local` extra.
HTTPX is already a development dependency and a Gemini runtime dependency; it
does not become a base dependency. A caller may inject an `httpx.Client`, so
tests use `MockTransport` and never open a socket.

Requests accept the same minimal shape as `OpenAIProvider` and
`GeminiProvider`: a non-empty `messages` list containing only `system`, `user`,
or `assistant` text messages, plus optional positive `max_tokens`. The adapter
normalizes plain text, model, finish reason, and prompt/completion token counts
into the established five-key response shape. It does not expand shared
result models for runtime-specific fields.

Health checking performs a bounded one-token chat completion through the same
explicit endpoint. It happens only when `check_health()` is called: imports
and construction perform no network access.

Transport failures, timeouts, authentication failures, HTTP failures, and
malformed responses translate into local-provider `ProviderError` subclasses.
Error text never includes authorization headers, API keys, or response bodies.
Retries are bounded by `max_retries` and apply only to timeout/transport
failures, never authentication, HTTP status, validation, or response-shape
failures.

## Architecture comparison

### Ollama-native API

Ollama has a useful native schema and model-management surface, but selecting
it would couple the kernel to one runtime and tempt model listing/pulling and
runtime lifecycle features that are explicitly out of scope. Ollama already
offers an OpenAI-compatible endpoint for this sprint's text-chat subset.

### OpenAI-compatible local endpoints

Selected. The protocol is stable, small, testable with ordinary HTTP, and
shared by multiple independent local runtimes. It fits the existing request
and response mappings without changing `BaseProvider`.

### vLLM-compatible serving

vLLM is production-oriented and implements the selected protocol, but a
vLLM-named adapter would add runtime coupling without gaining a capability
representable by the current kernel contract.

### LM Studio-compatible serving

LM Studio also implements the selected protocol. A dedicated adapter would be
desktop-runtime-specific and otherwise duplicate the same behavior.

### Generic local HTTP provider abstraction

Rejected. “Generic HTTP” has no interoperable request, response, health, usage,
or error schema. Making all of those configurable would create a template/DSL
or a large runtime-specific option surface rather than a small provider.

## Security and trust boundary

“Local” describes deployment ownership, not network safety. `base_url` is a
caller-controlled network destination and may target loopback, a LAN service,
or a remote private host. Products must treat endpoint configuration as
privileged and apply their own egress/SSRF policy. The kernel validates URL
shape but deliberately does not resolve DNS or impose a network topology: such
policy belongs at deployment boundaries and cannot be decided correctly by a
provider adapter.

The adapter never launches a process, starts a server, pulls a model, runs a
shell command, evaluates code, probes at import/construction time, or falls
back to the internet or another provider.

## Intentionally unsupported

Streaming, tools/function calls, structured-output modes, multimodal/vision
input, embeddings, model discovery, model pulling, runtime installation,
runtime startup/shutdown, batching, and endpoint failover are not exposed.
They either lack a shared `BaseProvider` contract or belong to runtime
management rather than model invocation.

## Consequences

- One additive adapter targets the OpenAI-compatible protocol implemented by
  multiple caller-managed serving runtimes. Runtime-specific interoperability
  requires separate validation and is not certified by this decision.
- Endpoint and runtime ownership remain entirely with the caller.
- Compatibility is limited to the documented Chat Completions subset; servers
  claiming compatibility but returning a different schema fail explicitly.
- Existing Claude, OpenAI, and Gemini code and behavior remain unchanged.
