"""Tests for mellivor_kernel.core.logging."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from mellivor_kernel.core import (
    ConfigurationError,
    add_file_handler,
    configure_logging,
    get_logger,
)
from mellivor_kernel.core.logging import _CONSOLE_HANDLER_ATTR

_ROOT_LOGGER_NAME = "mellivor_kernel"


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Iterator[None]:
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    yield
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def test_configure_logging_sets_level() -> None:
    logger = configure_logging(_FakeSettings(log_level="WARNING"))

    assert logger.level == logging.WARNING


def test_configure_logging_replaces_console_handler_on_reconfigure() -> None:
    configure_logging(_FakeSettings(log_level="INFO"))
    logger = configure_logging(_FakeSettings(log_level="DEBUG"))

    # Other tooling (e.g. pytest's own log capture) may attach further
    # handlers to this logger once `propagate` is False; only the handler
    # `configure_logging` itself owns is expected to stay singular.
    own_handlers = [h for h in logger.handlers if getattr(h, _CONSOLE_HANDLER_ATTR, False)]
    assert len(own_handlers) == 1
    assert logger.level == logging.DEBUG


def test_configure_logging_rejects_invalid_level() -> None:
    with pytest.raises(ConfigurationError):
        configure_logging(_FakeSettings(log_level="NOPE"))


def test_get_logger_is_namespaced_under_root() -> None:
    logger = get_logger("some.module")

    assert logger.name == f"{_ROOT_LOGGER_NAME}.some.module"


def test_add_file_handler_writes_structured_json_records(tmp_path: Path) -> None:
    configure_logging(_FakeSettings(log_level="INFO"))
    logger = get_logger("test_add_file_handler")
    log_file = tmp_path / "nested" / "kernel.log"

    handler = add_file_handler(logger, log_file)
    logger.info("hello from file handler")
    handler.flush()

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["message"] == "hello from file handler"
    assert record["level"] == "INFO"
    assert record["logger"] == logger.name


def test_add_file_handler_rejects_invalid_level(tmp_path: Path) -> None:
    logger = get_logger("test_add_file_handler_invalid_level")

    with pytest.raises(ConfigurationError):
        add_file_handler(logger, tmp_path / "kernel.log", level="NOPE")


def test_add_file_handler_records_exception_info(tmp_path: Path) -> None:
    configure_logging(_FakeSettings(log_level="INFO"))
    logger = get_logger("test_add_file_handler_exc_info")
    log_file = tmp_path / "kernel.log"

    handler = add_file_handler(logger, log_file)
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("something failed")
    handler.flush()

    record = json.loads(log_file.read_text(encoding="utf-8").strip().splitlines()[0])
    assert record["message"] == "something failed"
    assert "ValueError: boom" in record["exc_info"]
