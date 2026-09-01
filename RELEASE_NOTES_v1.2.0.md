# Mellivor Kernel v1.2.0

Commit: this release commit (`release(v1.2): prepare Mellivor Kernel 1.2.0`)

Branch: `main`

Tag: `v1.2.0` — to be applied manually after Product Owner approval.

## Summary

Mellivor Kernel 1.2.0 is a backward-compatible MINOR release under ADR-0005.
Its only capability addition is Sprint 32 `LocalProvider`, governed by
ADR-0026, for caller-managed OpenAI-compatible Chat Completions endpoints.
No existing v1.1 implementation or public contract changed.

## Public addition

- `providers.local.LocalProvider`
- `LocalProviderError`, `LocalAuthenticationError`, `LocalTimeoutError`,
  `LocalConnectionError`, and `LocalResponseError`
- Optional `local` dependency extra

Concrete providers remain explicitly importable from their provider-specific
modules. `BaseProvider`, `ProviderConfiguration`, `ProviderCapabilities`,
`ProviderRegistry`, `ProviderFactory`, and existing providers are unchanged.

## Dependencies

The base package still has no runtime dependency. Install LocalProvider's
transport only when needed:

```bash
pip install "mellivor-kernel[local]==1.2.0"
```

The `local` extra directly declares `httpx>=0.28.1,<1`. It does not install or
use the OpenAI, Anthropic, or Google provider SDKs.

## Compatibility and validation scope

Deterministic tests validate the documented OpenAI-compatible Chat
Completions subset: text messages with system, user, and assistant roles;
configured model selection; optional Bearer authentication; timeout and
bounded retry handling; provider-level error translation; response and token
usage normalization; health checks; and factory, registry, AI engine, and
execution-engine integration.

Sprint 32 did not test a real Ollama, LM Studio, or vLLM deployment. This
release therefore makes no runtime-specific or model-build certification.
Real-runtime validation being unavailable does not block the generic protocol
adapter, but it does preclude stronger interoperability claims.

## Security and trust boundary

The caller selects, trusts, deploys, and operates the endpoint. Kernel does
not resolve that deployment trust decision or silently redirect requests.
LocalProvider disables redirects and environment-proxy inheritance for its
owned HTTP client, translates transport failures at the provider boundary,
and excludes credentials, authorization headers, and response bodies from
its diagnostics.

Kernel does not install or start runtimes, manage processes, execute shell
commands, download models, discover models, or fall back to cloud providers.

## Upgrade from v1.1.0

```bash
pip install --upgrade mellivor-kernel==1.2.0
```

Existing v1.1 consumers require no source changes. Consumers that use the new
adapter install `[local]`, configure an explicit trusted `base_url` and
`default_model`, and remain responsible for the endpoint lifecycle.

## Intentionally excluded

This release does not include agent planning/reasoning, multi-agent
coordination, embeddings/vector/RAG, distributed events or message brokers,
plugin marketplaces, identity/OAuth/RBAC, vendor telemetry, persistent
scheduling, runtime management, or any other Future Research capability.

## Verification

Sprint 33 verified 896 tests, Ruff lint and formatting, strict MyPy, wheel and
sdist builds, artifact metadata, isolated dependency-free base installation,
isolated `[local]` installation, and GitHub Actions on Python 3.12 and 3.13.
See the complete [v1.2 release audit](docs/release/v1.2-release-audit.md).
