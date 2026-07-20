"""Kernel logging: structured console and file handlers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.exceptions import ConfigurationError

_ROOT_LOGGER_NAME = "mellivor_kernel"
_CONSOLE_HANDLER_ATTR = "_mellivor_console_handler"


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as a single-line JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON-encoded string representing the record.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _resolve_level(level_name: str) -> int:
    """Resolve a logging level name to its numeric value.

    Args:
        level_name: A logging severity level name, for example ``"INFO"``.

    Returns:
        The numeric logging level.

    Raises:
        ConfigurationError: If ``level_name`` does not name a known level.
    """
    levels = logging.getLevelNamesMapping()
    try:
        return levels[level_name]
    except KeyError as exc:
        valid = ", ".join(sorted(name for name in levels if name != "NOTSET"))
        raise ConfigurationError(
            f"Invalid log level {level_name!r}; expected one of: {valid}."
        ) from exc


def configure_logging(settings: KernelSettings) -> logging.Logger:
    """Configure the kernel's root logger from ``settings``.

    Idempotent: calling this again (for example, after a restart with new
    settings) replaces the console handler instead of stacking another one.
    File handlers attached via :func:`add_file_handler` are left untouched.

    Args:
        settings: An object exposing a ``log_level`` attribute naming a
            valid ``logging`` severity level.

    Returns:
        The configured root logger for the ``mellivor_kernel`` namespace.

    Raises:
        ConfigurationError: If ``settings.log_level`` does not name a valid
            logging severity level.
    """
    level = _resolve_level(settings.log_level)

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    for handler in [h for h in logger.handlers if getattr(h, _CONSOLE_HANDLER_ATTR, False)]:
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    setattr(console_handler, _CONSOLE_HANDLER_ATTR, True)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under the kernel's logging hierarchy.

    Args:
        name: A dotted name for the logger, typically the calling module's
            ``__name__``.

    Returns:
        A logger that propagates records to the configured kernel root
        logger.
    """
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def add_file_handler(
    logger: logging.Logger, path: Path, *, level: str | None = None
) -> logging.Handler:
    """Attach a minimal structured file handler to ``logger``.

    Args:
        logger: The logger to attach the handler to.
        path: The file to append log records to. Parent directories are
            created if they do not already exist.
        level: An optional level name restricting this handler to records
            at or above that severity. Defaults to no restriction beyond
            the logger's own effective level.

    Returns:
        The attached handler.

    Raises:
        ConfigurationError: If ``level`` is provided but does not name a
            valid logging severity level.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(StructuredFormatter())
    if level is not None:
        handler.setLevel(_resolve_level(level))
    logger.addHandler(handler)
    return handler
