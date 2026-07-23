"""Memory subsystem exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class MemoryError(KernelError):
    """Base class for all errors raised by the memory subsystem.

    Raised only for invalid data (a malformed
    :class:`~mellivor_kernel.memory.entry.MemoryEntry`) -- a missing
    lookup or an empty search result is a normal, non-raising outcome
    (``None`` or an empty :class:`~mellivor_kernel.memory.result.MemoryResult`).

    Shadows the built-in :class:`MemoryError` within this package's own
    namespace; this is the kernel's memory subsystem, not an out-of-memory
    condition. Unqualified code elsewhere is unaffected -- Python's normal
    scoping rules apply.
    """
