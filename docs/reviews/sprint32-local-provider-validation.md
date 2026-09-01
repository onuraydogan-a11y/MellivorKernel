# Sprint 32 LocalProvider Validation

## Status

Validated for the documented OpenAI-compatible Chat Completions protocol
subset. This validation does not constitute a v1.2 release decision.

## Compatibility audit

`LocalProvider` is additive relative to v1.1.0. It subclasses the unchanged
`BaseProvider`, consumes the unchanged `ProviderConfiguration`, and is
imported explicitly from `mellivor_kernel.providers.local`, following the
existing concrete-provider isolation convention. No v1.1 provider contract,
configuration field, registry/factory behavior, or existing provider module
was changed.

The adapter preserves system, user, and assistant text messages, selects the
configured default model, sends requests to the configured base URL plus
`/chat/completions`, and normalizes text, model, finish reason, and token usage.
Optional credentials are sent only as a Bearer header. Timeouts, transport
failures, authentication failures, HTTP failures, and malformed responses are
translated into `ProviderError` subclasses without response bodies,
credentials, or authorization headers in error messages.

Factory, registry, AI engine, and full execution-engine paths are covered by
deterministic integration tests. Import and construction perform no network
access. The implementation contains no subprocess, shell, runtime-management,
model-download, model-discovery, or cloud-fallback behavior.

## Runtime validation

No already-running Ollama, LM Studio, or vLLM endpoint was available in the
validation environment. No runtime was installed or started and no model was
downloaded. The verified claim is therefore protocol compatibility through
injected HTTPX transports, not proven interoperability with a particular
runtime or model build.

Before making a runtime-specific interoperability claim, validate the same
request, response, authentication, timeout, and health-check paths against a
caller-managed endpoint in an appropriate integration environment.

## Dependencies and versioning

Base runtime dependencies remain empty. The `local` extra directly owns
`httpx>=0.28.1,<1`; LocalProvider does not use OpenAI SDK internals or rely on
a transitive provider dependency.

ADR-0005 establishes SemVer release behavior but no development-version
scheme. Existing repository history updates `version.py` during release
preparation, so it remains `1.1.0` until a future release gate approves a new
version. The post-v1.1 LocalProvider work is recorded under `Unreleased` in
`CHANGELOG.md`; no v1.2 scope, version, or tag is created by this validation.
