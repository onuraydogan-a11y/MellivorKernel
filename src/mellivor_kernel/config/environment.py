"""Runtime environment classification for the kernel."""

from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    """The runtime environment the kernel is operating in.

    Attributes:
        DEVELOPMENT: Local development; verbose defaults are appropriate.
        TEST: Automated test execution.
        PRODUCTION: A live production deployment.
    """

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
