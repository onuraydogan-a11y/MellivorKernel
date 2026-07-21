"""The tool contract every kernel tool must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from mellivor_kernel.tools.context import ToolContext
from mellivor_kernel.tools.metadata import ToolMetadata
from mellivor_kernel.tools.permissions import Permission
from mellivor_kernel.tools.result import ToolResult


class BaseTool(ABC):
    """The contract every kernel tool must implement.

    Concrete tools declare their identity through the abstract properties
    below and implement :meth:`validate` and :meth:`execute`;
    :meth:`metadata` is provided and needs no override.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """A short, unique identifier for this tool, e.g. ``"echo"``."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """A human-readable name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """The tool's own version string, independent of the kernel's version."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """A human-readable description of what this tool does."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[str]:
        """Free-form tags describing what this tool can do."""
        ...

    @property
    @abstractmethod
    def permissions(self) -> frozenset[Permission]:
        """The permissions this tool requires to execute."""
        ...

    def metadata(self) -> ToolMetadata:
        """Return a snapshot of this tool's identity and requirements.

        Returns:
            A :class:`ToolMetadata` built from this tool's declared
            properties.
        """
        return ToolMetadata(
            id=self.id,
            name=self.name,
            version=self.version,
            description=self.description,
            capabilities=self.capabilities,
            permissions=self.permissions,
        )

    @abstractmethod
    def validate(self, request: Mapping[str, object]) -> None:
        """Validate a request before it is executed.

        Args:
            request: The request payload that will be passed to
                :meth:`execute` if validation succeeds.

        Raises:
            ToolValidationError: If ``request`` is not valid for this tool.
        """
        ...

    @abstractmethod
    def execute(self, context: ToolContext, request: Mapping[str, object]) -> ToolResult:
        """Execute this tool.

        Args:
            context: The kernel-provided execution context.
            request: The (already validated) request payload.

        Returns:
            The outcome of the execution.
        """
        ...
