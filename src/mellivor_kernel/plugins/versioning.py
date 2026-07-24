"""Minimal `MAJOR.MINOR.PATCH` version parsing for plugin compatibility checks.

Deliberately narrow: this kernel's own `__version__` (see ADR-0005) is
always plain `MAJOR.MINOR.PATCH`, with no pre-release or build-metadata
segments, so plugin manifests are held to the same shape rather than
depending on a general-purpose version-parsing library.
"""

from __future__ import annotations

from mellivor_kernel.plugins.exceptions import PluginValidationError


def parse_version(value: str, *, field_name: str) -> tuple[int, int, int]:
    """Parse a `MAJOR.MINOR.PATCH` version string into a comparable tuple.

    Args:
        value: The version string to parse.
        field_name: The name of the field being validated, used in the
            error message.

    Returns:
        A `(major, minor, patch)` tuple of non-negative integers.

    Raises:
        PluginValidationError: If `value` is not exactly three
            dot-separated non-negative integers.
    """
    parts = value.strip().split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise PluginValidationError(
            f"{field_name} must be a MAJOR.MINOR.PATCH version string, got {value!r}."
        )
    major, minor, patch = (int(part) for part in parts)
    return (major, minor, patch)
