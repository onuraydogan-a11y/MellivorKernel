"""Observation context for the kernel's reusable observability foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ObservationContext:
    """A lightweight propagation container for correlation and tracing metadata."""

    correlation_id: str = field(default_factory=lambda: f"corr-{uuid4().hex}")
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> ObservationContext:
        """Create a new observation context, minting a correlation ID when omitted."""
        return cls(
            correlation_id=correlation_id or f"corr-{uuid4().hex}",
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {},
        )
