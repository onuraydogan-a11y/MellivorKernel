"""Tool metadata: a snapshot of a tool's static, self-declared identity."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.tools.permissions import Permission


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """A snapshot of a tool's static identity and declared requirements.

    Attributes:
        id: A short, unique identifier for the tool, e.g. ``"echo"``.
        name: A human-readable name.
        version: The tool's own version string (independent of the
            kernel's version).
        description: A human-readable description of what the tool does.
        capabilities: Free-form tags describing what the tool can do.
        permissions: The permissions the tool requires to execute.
    """

    id: str
    name: str
    version: str
    description: str
    capabilities: frozenset[str]
    permissions: frozenset[Permission]
