# `config` subsystem spec

Status: Implemented (Sprint 2)

Public contract exported from `mellivor_kernel.config`. Anything not listed
here is internal and carries no compatibility guarantee, per
[ADR-0004](../adr/0004-public-api-philosophy.md).

## `Environment`

A `StrEnum` naming the runtime environment: `DEVELOPMENT`, `TEST`,
`PRODUCTION`.

## `KernelConfig`

An immutable (`frozen=True, slots=True`) dataclass:

- `environment: Environment = Environment.DEVELOPMENT`
- `log_level: str = "INFO"` — must name a valid `logging` severity level;
  validated in `__post_init__`.
- `debug: bool = False`

Raises `ConfigurationError` (re-exported from `core`) on construction if
`log_level` is invalid.

## `load_config`

`load_config(env: Mapping[str, str] | None = None) -> KernelConfig`

Loads and validates configuration from environment variables, defaulting to
`os.environ` (an explicit mapping may be passed, primarily for testing).
Recognized variables, all falling back to `KernelConfig`'s defaults when
absent:

- `MELLIVOR_ENVIRONMENT` — case-insensitive; must match an `Environment`
  value.
- `MELLIVOR_LOG_LEVEL` — case-insensitive; must name a valid logging
  severity level.
- `MELLIVOR_DEBUG` — accepts (case-insensitively) `1`/`true`/`yes`/`on` or
  `0`/`false`/`no`/`off`.

Raises `ConfigurationError` if any recognized variable is present but
invalid.
