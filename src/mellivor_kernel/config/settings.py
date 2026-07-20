"""Central kernel configuration: the validated ``KernelConfig`` object and
environment-variable loading.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from mellivor_kernel.config.environment import Environment
from mellivor_kernel.core.exceptions import ConfigurationError

_ENV_VAR_PREFIX = "MELLIVOR_"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True, slots=True)
class KernelConfig:
    """Immutable, validated configuration for a running kernel instance.

    Attributes:
        environment: The runtime environment the kernel is operating in.
        log_level: The minimum severity of log records the kernel emits.
            Must name a valid ``logging`` severity level, for example
            ``"DEBUG"`` or ``"INFO"``.
        debug: Whether verbose/debug behavior is enabled.
    """

    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate field values.

        Raises:
            ConfigurationError: If ``log_level`` does not name a valid
                logging severity level.
        """
        valid_levels = logging.getLevelNamesMapping()
        if self.log_level not in valid_levels:
            valid = ", ".join(sorted(name for name in valid_levels if name != "NOTSET"))
            raise ConfigurationError(
                f"Invalid log_level {self.log_level!r}; expected one of: {valid}."
            )


def _parse_environment(raw_value: str) -> Environment:
    """Parse an ``Environment`` from a raw environment-variable string.

    Args:
        raw_value: The raw string value to parse.

    Returns:
        The matching ``Environment`` member.

    Raises:
        ConfigurationError: If ``raw_value`` does not match a known
            environment.
    """
    try:
        return Environment(raw_value.strip().lower())
    except ValueError as exc:
        valid = ", ".join(member.value for member in Environment)
        raise ConfigurationError(
            f"Invalid {_ENV_VAR_PREFIX}ENVIRONMENT value {raw_value!r}; expected one of: {valid}."
        ) from exc


def _parse_bool(raw_value: str, *, variable_name: str) -> bool:
    """Parse a boolean from a raw environment-variable string.

    Args:
        raw_value: The raw string value to parse.
        variable_name: The environment variable name, used in error
            messages.

    Returns:
        The parsed boolean value.

    Raises:
        ConfigurationError: If ``raw_value`` does not match a recognized
            boolean representation.
    """
    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    valid = ", ".join(sorted(_TRUE_VALUES | _FALSE_VALUES))
    raise ConfigurationError(
        f"Invalid {variable_name} value {raw_value!r}; expected one of: {valid}."
    )


def load_config(env: Mapping[str, str] | None = None) -> KernelConfig:
    """Load and validate kernel configuration from environment variables.

    Recognized variables: ``MELLIVOR_ENVIRONMENT``, ``MELLIVOR_LOG_LEVEL``,
    ``MELLIVOR_DEBUG``. Any variable that is absent falls back to the
    corresponding ``KernelConfig`` default.

    Args:
        env: The environment mapping to read from. Defaults to
            ``os.environ``. Primarily overridable for testing.

    Returns:
        A validated, immutable ``KernelConfig``.

    Raises:
        ConfigurationError: If any recognized variable is present but
            invalid.
    """
    source: Mapping[str, str] = env if env is not None else os.environ
    defaults = KernelConfig()

    environment = defaults.environment
    if (raw_environment := source.get(f"{_ENV_VAR_PREFIX}ENVIRONMENT")) is not None:
        environment = _parse_environment(raw_environment)

    log_level = defaults.log_level
    if (raw_log_level := source.get(f"{_ENV_VAR_PREFIX}LOG_LEVEL")) is not None:
        log_level = raw_log_level.strip().upper()

    debug = defaults.debug
    if (raw_debug := source.get(f"{_ENV_VAR_PREFIX}DEBUG")) is not None:
        debug = _parse_bool(raw_debug, variable_name=f"{_ENV_VAR_PREFIX}DEBUG")

    return KernelConfig(environment=environment, log_level=log_level, debug=debug)
