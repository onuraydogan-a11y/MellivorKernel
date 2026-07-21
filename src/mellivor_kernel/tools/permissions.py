"""The tool permission model.

Permissions are free-form, dotted string identifiers (for example
``"network.read"`` or ``"filesystem.write"``). The kernel validates their
*format* but does not maintain a fixed vocabulary of permission names --
domain-specific permissions (for example a hypothetical ``"crm.read"``
declared by a consuming application's own tool) are valid strings the
kernel neither defines nor interprets, consistent with the kernel staying
business-agnostic (see ``docs/adr/0003-repository-boundaries.md``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mellivor_kernel.tools.exceptions import ToolValidationError

_PERMISSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


@dataclass(frozen=True, slots=True)
class Permission:
    """A single, validated permission identifier.

    Attributes:
        value: The dotted permission string, for example
            ``"filesystem.read"``. Must be lowercase, dot-separated
            segments of alphanumerics/underscores, with at least one dot.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate ``value``'s format.

        Raises:
            ToolValidationError: If ``value`` does not match the required
                dotted-identifier format.
        """
        if not _PERMISSION_PATTERN.match(self.value):
            raise ToolValidationError(
                f"Invalid permission {self.value!r}; expected a dotted, lowercase "
                "identifier such as 'filesystem.read'."
            )

    def __str__(self) -> str:
        """Return the permission's dotted string form."""
        return self.value


def missing_permissions(
    required: frozenset[Permission], granted: frozenset[Permission]
) -> frozenset[Permission]:
    """Return the subset of ``required`` not present in ``granted``.

    Args:
        required: The permissions a tool declares it needs.
        granted: The permissions available to the current execution.

    Returns:
        The permissions in ``required`` that are missing from ``granted``.
        Empty if every required permission is granted.
    """
    return required - granted


# Well-known, infrastructure-level permissions the kernel itself defines.
# Business-specific permissions (e.g. a hypothetical "crm.read") are valid
# `Permission` values but are never defined here -- see the module docstring.
NETWORK_READ = Permission("network.read")
FILESYSTEM_READ = Permission("filesystem.read")
FILESYSTEM_WRITE = Permission("filesystem.write")
PROVIDER_INVOKE = Permission("provider.invoke")
KERNEL_INTERNAL = Permission("kernel.internal")
