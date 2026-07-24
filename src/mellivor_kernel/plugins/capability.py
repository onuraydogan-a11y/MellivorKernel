"""PluginCapability: a single, named capability a plugin declares."""

from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.plugins.exceptions import PluginValidationError


@dataclass(frozen=True, slots=True)
class PluginCapability:
    """A single, named capability a plugin declares it provides.

    Deliberately free-form: the kernel does not enumerate a fixed
    vocabulary of capability kinds (mirroring how `tools.BaseTool
    .capabilities` is a plain `frozenset[str]`, not a closed enum) -- a
    capability name is an agreement between a plugin author and whatever
    future consumer inspects it, not something this foundation sprint
    prescribes.

    Attributes:
        name: A short, unique-within-a-plugin identifier for the
            capability, e.g. `"workflow.step"`.
        description: A human-readable description of the capability.
    """

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        """Validate field values.

        Raises:
            PluginValidationError: If `name` is blank.
        """
        if not self.name.strip():
            raise PluginValidationError("PluginCapability.name must not be blank.")
