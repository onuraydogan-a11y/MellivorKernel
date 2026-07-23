"""Agent runtime exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class AgentError(KernelError):
    """Base class for all errors raised by the agent runtime.

    Raised only for invalid data (a malformed
    :class:`~mellivor_kernel.agents.definition.AgentDefinition` or
    :class:`~mellivor_kernel.agents.result.AgentResult`) -- a workflow
    failing during a run is a normal, non-raising outcome, represented in
    :class:`~mellivor_kernel.agents.result.AgentResult`.
    """
