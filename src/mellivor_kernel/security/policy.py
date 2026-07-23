"""Security policy primitives for the kernel's reusable security foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityDecision:
    """The outcome of evaluating a security policy."""

    allowed: bool
    reason: str = ""
