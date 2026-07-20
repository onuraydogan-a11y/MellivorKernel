"""Shared structural contracts used within the kernel core.

These protocols let ``core`` depend on the *shape* of configuration it
needs without importing the ``config`` subsystem, keeping ``core`` free of
dependencies on subsystems that in turn depend on it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class KernelSettings(Protocol):
    """The subset of configuration the kernel runtime depends on.

    Declared as a read-only property so that immutable implementations
    (such as a frozen dataclass) satisfy this contract.
    """

    @property
    def log_level(self) -> str:
        """The name of a valid ``logging`` severity level to log at."""
        ...
