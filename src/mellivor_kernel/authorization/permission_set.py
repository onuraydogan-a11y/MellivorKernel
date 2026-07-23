"""PermissionSet: an immutable collection of permissions."""

from __future__ import annotations

from dataclasses import dataclass, field

from mellivor_kernel.tools.permissions import Permission


@dataclass(frozen=True, slots=True)
class PermissionSet:
    """An immutable, validated collection of :class:`Permission` values.

    Wraps the existing tool permission model (see
    ``docs/specs/tools.md``'s permission model) -- no new permission
    vocabulary is introduced. Empty by default.

    Attributes:
        permissions: The permissions in this set.
    """

    permissions: frozenset[Permission] = field(default_factory=frozenset)

    @classmethod
    def empty(cls) -> PermissionSet:
        """Return an empty ``PermissionSet``."""
        return cls()
