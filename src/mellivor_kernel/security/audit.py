"""Audit contracts for the kernel's reusable security foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from mellivor_kernel.security.policy import SecurityDecision


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """A structured audit event emitted by the security foundation."""

    event: str
    subject: str
    action: str
    decision: SecurityDecision


@runtime_checkable
class AuditSink(Protocol):
    """A structural contract for recording audit events."""

    def record(self, record: AuditRecord) -> None:
        """Persist or emit ``record``."""
        ...
