"""Structured event records for the kernel's observability foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mellivor_kernel.observability.context import ObservationContext


@dataclass(frozen=True, slots=True)
class StructuredObservationEvent:
    """A serializable, structured observation event.

    This is intentionally small and framework-agnostic: a consumer can emit it
    to logs, memory, or any external sink without coupling the kernel to a
    specific telemetry backend.
    """

    name: str
    message: str
    context: ObservationContext
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary representation of the event."""
        return {
            "name": self.name,
            "message": self.message,
            "context": {
                "correlation_id": self.context.correlation_id,
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "attributes": dict(self.context.attributes),
            },
            "attributes": dict(self.attributes),
        }
