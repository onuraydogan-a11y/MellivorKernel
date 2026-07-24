"""Resolves a discovery `entry_point` string into a zero-argument Plugin
factory.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

from mellivor_kernel.plugin_discovery.exceptions import EntryPointError
from mellivor_kernel.plugins import Plugin


def resolve_entry_point(entry_point: str) -> Callable[[], Plugin]:
    """Resolve `entry_point` (`"module.path:AttributeName"`) into a callable.

    Args:
        entry_point: A `"module:attribute"` string naming a zero-argument
            callable that constructs a `Plugin` instance.

    Returns:
        The resolved callable.

    Raises:
        EntryPointError: If `entry_point` is not in `module:attribute`
            format, the module cannot be imported, the attribute does not
            exist on it, or the resolved attribute is not callable.
    """
    module_name, sep, attr_name = entry_point.partition(":")
    if not sep or not module_name or not attr_name:
        raise EntryPointError(f"Entry point {entry_point!r} must be in 'module:attribute' format.")

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise EntryPointError(
            f"Could not import module {module_name!r} for entry point {entry_point!r}: {exc}"
        ) from exc

    try:
        attribute = getattr(module, attr_name)
    except AttributeError as exc:
        raise EntryPointError(
            f"Module {module_name!r} has no attribute {attr_name!r} "
            f"for entry point {entry_point!r}."
        ) from exc

    if not callable(attribute):
        raise EntryPointError(f"Resolved entry point {entry_point!r} is not callable.")

    factory: Callable[[], Plugin] = attribute
    return factory
